"""server/game/shard_app.py

Entry point for one Game Server SHARD in the split architecture
(Server_Design.md Sec.1/7). A shard no longer talks to real clients
directly - it accepts internal connections from:

  1. The WS Gateway - one persistent, multiplexed connection carrying many
     real clients' traffic, tagged by conn_id (KIND_CLIENT_*).
  2. The Matchmaking service - one-shot control calls that pre-register a
     GameSession with the correct white/black identity BEFORE either
     player connects (KIND_CREATE_SESSION). This preserves the
     identity-based color assignment fix in GameSession.assign_color -
     without it, a matched room would fall back to first-connect-wins
     ordering, reintroducing the exact race condition that was already
     fixed once.

For each conn_id the Gateway opens, this module runs the *same*
handle_client() coroutine used for direct connections - the shard's game
logic (GameSession, GameEngine) is completely unaware whether a client
is local or proxied through the Gateway.
"""

import asyncio
import json
import os

import websockets
from aiohttp import web

from server.core.database import init_db
from server.core.observability import get_logger, build_health_response, check_postgres, check_redis
from server.core.internal_protocol import (
    SHARD_INTERNAL_PORT,
    NUM_SHARDS,
    KIND_CLIENT_OPEN,
    KIND_CLIENT_MESSAGE,
    KIND_CLIENT_CLOSE,
    KIND_SERVER_MESSAGE,
    KIND_SERVER_CLOSE,
    KIND_CREATE_SESSION,
    shard_channel,
)
from server.core.redis_client import set_room_shard, subscribe as redis_subscribe
from server.game.connection import handle_client
from server.game.session import GameSession, register_session

SHARD_INDEX = int(os.environ.get("SHARD_INDEX", "0"))
HOST = os.environ.get("HOST", "0.0.0.0")
HEALTH_PORT = int(os.environ.get("SHARD_HEALTH_PORT", str(9600 + 1)))

_log = get_logger(f"game-server-{SHARD_INDEX}")


class RemoteClientSocket:
    """Stands in for a real websockets connection for one Gateway-proxied
    client. Fulfils the same duck-typed interface handle_client() already
    requires: async send(str), async close(), async-iterate raw messages.
    Every outgoing frame is tagged with conn_id and written back onto the
    ONE shared internal connection to the Gateway - never used to open a
    new socket per client."""

    def __init__(self, conn_id: str, internal_ws):
        self._conn_id = conn_id
        self._internal_ws = internal_ws
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def send(self, payload: str):
        if self._closed:
            return
        await self._internal_ws.send(json.dumps({
            "kind": KIND_SERVER_MESSAGE, "conn_id": self._conn_id, "data": payload,
        }))

    async def close(self):
        if self._closed:
            return
        self._closed = True
        await self._internal_ws.send(json.dumps({"kind": KIND_SERVER_CLOSE, "conn_id": self._conn_id}))

    def feed(self, raw: str | None):
        """Called by the internal-connection reader loop below. None is the
        close sentinel - it ends the `async for raw in client_socket` loop
        inside Connection.run(), which triggers its existing `finally`
        cleanup (on_disconnect / forfeit-grace) exactly as a real socket
        closing would."""
        self._queue.put_nowait(raw)

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item


async def _pubsub_listener():
    """Subscribe to this shard's Redis channel and handle create_session
    events published by Matchmaking. Runs as a background task alongside
    the WebSocket server. If Redis is unavailable, exits silently —
    Matchmaking falls back to the direct WebSocket path in that case."""
    pubsub = await redis_subscribe(shard_channel(SHARD_INDEX))
    if pubsub is None:
        _log.info("pubsub_unavailable", extra={"shard": SHARD_INDEX})
        return
    _log.info("pubsub_listening", extra={"channel": shard_channel(SHARD_INDEX)})
    try:
        async for raw in pubsub.listen():
            if raw["type"] != "message":
                continue
            try:
                envelope = json.loads(raw["data"])
            except (json.JSONDecodeError, TypeError):
                continue
            if envelope.get("kind") != KIND_CREATE_SESSION:
                continue
            session = GameSession(
                white_user_id=envelope["white_user_id"],
                white_elo=envelope.get("white_elo"),
                black_user_id=envelope["black_user_id"],
                black_elo=envelope.get("black_elo"),
            )
            register_session(envelope["room_id"], session)
            _log.info("session_created", extra={"room_id": envelope["room_id"], "via": "pubsub"})
    except Exception as e:
        _log.info("pubsub_error", extra={"error": str(e)})


async def _internal_connection_handler(internal_ws):
    """Handles ONE internal connection - either the Gateway's long-lived
    multiplexed channel, or a single one-shot Matchmaking control call."""
    live_conns: dict[str, RemoteClientSocket] = {}
    try:
        async for raw in internal_ws:
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError:
                continue
            kind = envelope.get("kind")

            if kind == KIND_CLIENT_OPEN:
                conn_id = envelope["conn_id"]
                remote = RemoteClientSocket(conn_id, internal_ws)
                live_conns[conn_id] = remote
                asyncio.create_task(handle_client(remote, envelope["path"]))

            elif kind == KIND_CLIENT_MESSAGE:
                remote = live_conns.get(envelope["conn_id"])
                if remote is not None:
                    remote.feed(envelope["data"])

            elif kind == KIND_CLIENT_CLOSE:
                remote = live_conns.pop(envelope["conn_id"], None)
                if remote is not None:
                    remote.feed(None)

            elif kind == KIND_CREATE_SESSION:
                # Fire-and-forget: pre-register the session with verified
                # identities before either player has connected.
                session = GameSession(
                    white_user_id=envelope["white_user_id"],
                    white_elo=envelope.get("white_elo"),
                    black_user_id=envelope["black_user_id"],
                    black_elo=envelope.get("black_elo"),
                )
                register_session(envelope["room_id"], session)
                asyncio.create_task(set_room_shard(envelope["room_id"], SHARD_INDEX))
    finally:
        # Gateway connection dropped (crash/redeploy) - end every live
        # client's `async for` loop so GameSession.on_disconnect / the
        # existing GRACE_SECONDS forfeit logic runs, same as any other
        # disconnect (Server_Design.md Sec.3, WS Gateway row).
        for remote in live_conns.values():
            remote.feed(None)


async def main():
    init_db()
    _log.info("starting", extra={"shard": SHARD_INDEX, "port": SHARD_INTERNAL_PORT})

    async def handle_health(request: web.Request) -> web.Response:
        from server.game.session import _sessions
        checks = {
            "postgres": await check_postgres(),
            "redis": await check_redis(),
        }
        body = build_health_response(f"game-server-{SHARD_INDEX}", checks)
        body["active_sessions"] = len(_sessions)
        status = 200 if body["status"] == "ok" else 503
        return web.json_response(body, status=status)

    health_app = web.Application()
    health_app.router.add_get("/health", handle_health)
    health_runner = web.AppRunner(health_app)
    await health_runner.setup()
    await web.TCPSite(health_runner, HOST, HEALTH_PORT).start()

    asyncio.create_task(_pubsub_listener())

    async with websockets.serve(_internal_connection_handler, HOST, SHARD_INTERNAL_PORT):
        print(f"Game Server shard {SHARD_INDEX}/{NUM_SHARDS} - internal listener on ws://{HOST}:{SHARD_INTERNAL_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
