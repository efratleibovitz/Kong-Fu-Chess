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

from server.core.database import init_db
from server.matchmaking.handler import matchmaking_handler

HOST = os.environ.get("HOST", "0.0.0.0")
MATCHMAKING_PORT = int(os.environ.get("MATCHMAKING_PORT", "8766"))


async def main():
    init_db()
    async with websockets.serve(matchmaking_handler, HOST, MATCHMAKING_PORT):
        print(f"Matchmaking service on ws://{HOST}:{MATCHMAKING_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
