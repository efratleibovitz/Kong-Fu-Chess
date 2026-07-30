"""server/gateway/app.py

WS Gateway (Server_Design.md Sec.1/2). The only game-traffic component
that's internet-facing. Holds real client sockets; holds NO game state and
makes NO game-rule decisions - it only knows "which shard owns this
room_id" (consistent hashing, server/core/internal_protocol.py) and relays
raw messages both directions. A client's TCP session lives here, not on a
Game Server pod, so a shard redeploy doesn't drop the client - it just
means the Gateway's next message to that room briefly waits/retries.

One persistent, multiplexed internal connection is kept open to each
shard (opened lazily, reused for every client whose room hashes there) -
NOT one internal connection per client, which would defeat the point.
"""

import asyncio
import json
import os
import uuid
from urllib.parse import urlparse, parse_qs, urlencode

import websockets
from aiohttp import web

from server.core.protocol import QUERY_ROOM_ID, QUERY_CREATE, FLAG_TRUE
from server.core.observability import get_logger, build_health_response, check_redis
from server.core.internal_protocol import (
    NUM_SHARDS,
    shard_index_for_room,
    shard_internal_url,
    KIND_CLIENT_OPEN,
    KIND_CLIENT_MESSAGE,
    KIND_CLIENT_CLOSE,
    KIND_SERVER_MESSAGE,
    KIND_SERVER_CLOSE,
)
from server.core.redis_client import get_room_shard

HOST = "0.0.0.0"
PUBLIC_PORT = 8765
HEALTH_PORT = int(os.environ.get("GATEWAY_HEALTH_PORT", "8768"))

_log = get_logger("ws-gateway")

# room_id -> local client websocket, for routing shard replies back out.
_clients: dict[str, "websockets.WebSocketServerProtocol"] = {}

# shard_url -> (connection, send-lock, reader-task). Lazily connected,
# shared by every client whose room hashes to that shard.
_shard_conns: dict[str, tuple] = {}
_shard_conns_lock = asyncio.Lock()


async def _get_shard_connection(shard_url: str):
    async with _shard_conns_lock:
        entry = _shard_conns.get(shard_url)
        if entry is not None:
            conn, lock, _task = entry
            if not conn.close_code:  # still open
                return conn, lock
        conn = await websockets.connect(shard_url)
        lock = asyncio.Lock()
        task = asyncio.create_task(_shard_reader(shard_url, conn))
        _shard_conns[shard_url] = (conn, lock, task)
        return conn, lock


async def _shard_reader(shard_url: str, conn):
    """One reader per shard connection, dispatches replies back to
    whichever local client conn_id they're tagged for."""
    try:
        async for raw in conn:
            envelope = json.loads(raw)
            conn_id = envelope.get("conn_id")
            client_ws = _clients.get(conn_id)
            if client_ws is None:
                continue
            if envelope["kind"] == KIND_SERVER_MESSAGE:
                await client_ws.send(envelope["data"])
            elif envelope["kind"] == KIND_SERVER_CLOSE:
                await client_ws.close()
    except websockets.ConnectionClosed:
        pass


def _resolve_path(raw_path: str) -> tuple[str, str]:
    """Ensures room_id is decided BEFORE hashing - a client creating a
    fresh room (no room_id yet) would otherwise let the shard invent one
    the Gateway never learns, breaking routing for the second player."""
    parsed = urlparse(raw_path)
    params = parse_qs(parsed.query)
    room_id = params.get(QUERY_ROOM_ID, [None])[0]
    create = params.get(QUERY_CREATE, [None])[0] == FLAG_TRUE
    if create and not room_id:
        room_id = str(uuid.uuid4())
        params[QUERY_ROOM_ID] = [room_id]
        new_query = urlencode({k: v[0] for k, v in params.items()})
        raw_path = f"{parsed.path}?{new_query}"
    return raw_path, room_id


async def _resolve_shard_url(room_id: str) -> str:
    index = await get_room_shard(room_id)
    if index is None:
        index = shard_index_for_room(room_id, NUM_SHARDS)
    from server.core.internal_protocol import SHARD_HOST_PATTERN, SHARD_INTERNAL_PORT
    host = SHARD_HOST_PATTERN.format(i=index)
    return f"ws://{host}:{SHARD_INTERNAL_PORT}"


async def client_handler(client_ws):
    conn_id = str(uuid.uuid4())
    path, room_id = _resolve_path(client_ws.request.path)

    if not room_id:
        # No room_id and not creating one - let the shard reject it with
        # the normal INVALID_ROOM error rather than special-casing here.
        room_id = "unrouted"

    shard_url = await _resolve_shard_url(room_id)
    conn, lock = await _get_shard_connection(shard_url)
    _clients[conn_id] = client_ws

    async with lock:
        await conn.send(json.dumps({"kind": KIND_CLIENT_OPEN, "conn_id": conn_id, "path": path}))

    try:
        async for raw in client_ws:
            async with lock:
                await conn.send(json.dumps({"kind": KIND_CLIENT_MESSAGE, "conn_id": conn_id, "data": raw}))
    finally:
        _clients.pop(conn_id, None)
        try:
            async with lock:
                await conn.send(json.dumps({"kind": KIND_CLIENT_CLOSE, "conn_id": conn_id}))
        except websockets.ConnectionClosed:
            pass


async def main():
    async def handle_health(request: web.Request) -> web.Response:
        checks = {"redis": await check_redis()}
        body = build_health_response("ws-gateway", checks)
        body["active_clients"] = len(_clients)
        body["shard_connections"] = len(_shard_conns)
        status = 200 if body["status"] == "ok" else 503
        return web.json_response(body, status=status)

    health_app = web.Application()
    health_app.router.add_get("/health", handle_health)
    health_runner = web.AppRunner(health_app)
    await health_runner.setup()
    await web.TCPSite(health_runner, HOST, HEALTH_PORT).start()

    async with websockets.serve(client_handler, HOST, PUBLIC_PORT):
        _log.info("starting", extra={"port": PUBLIC_PORT, "shards": NUM_SHARDS})
        print(f"WS Gateway on ws://{HOST}:{PUBLIC_PORT} -> {NUM_SHARDS} shard(s)")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
