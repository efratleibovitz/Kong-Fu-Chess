"""server/matchmaking/app.py

Standalone Matchmaking service entrypoint. Split out of the old
server/app.py (which ran matchmaking and the game server as one process -
fine when they shared memory, no longer valid now that Game Server is
split into separately-deployed shards). Still exposed directly to
clients on its own WS port, same as before (Server_Design.md Sec.1 notes
this as the one MVP simplification vs. routing matchmaking through the
WS Gateway too - not shard-routed, single replica, so it doesn't need it).
"""

import asyncio
import os

import websockets
from aiohttp import web

from server.core.database import init_db
from server.core.observability import get_logger, build_health_response, check_postgres, check_redis
from server.matchmaking.handler import matchmaking_handler

HOST = os.environ.get("HOST", "0.0.0.0")
MATCHMAKING_PORT = int(os.environ.get("MATCHMAKING_PORT", "8766"))
HEALTH_PORT = int(os.environ.get("MATCHMAKING_HEALTH_PORT", "8767"))

_log = get_logger("matchmaking")


async def handle_health(request: web.Request) -> web.Response:
    checks = {
        "postgres": await check_postgres(),
        "redis": await check_redis(),
    }
    body = build_health_response("matchmaking", checks)
    status = 200 if body["status"] == "ok" else 503
    return web.json_response(body, status=status)


async def main():
    init_db()
    _log.info("starting", extra={"host": HOST, "port": MATCHMAKING_PORT})

    health_app = web.Application()
    health_app.router.add_get("/health", handle_health)
    health_runner = web.AppRunner(health_app)
    await health_runner.setup()
    await web.TCPSite(health_runner, HOST, HEALTH_PORT).start()

    async with websockets.serve(matchmaking_handler, HOST, MATCHMAKING_PORT):
        print(f"Matchmaking service on ws://{HOST}:{MATCHMAKING_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
