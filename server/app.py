"""server/app.py

Entry point: initializes the database, starts the game and matchmaking
websocket servers, and routes incoming connections to their handlers.
"""

import asyncio
import websockets

from server.core.database import init_db
from server.core.protocol import HOST, PORT, MATCHMAKING_PORT
from server.game.connection import game_handler
from server.matchmaking.handler import matchmaking_handler


async def main():
    init_db()

    async with websockets.serve(game_handler, HOST, PORT), \
                websockets.serve(matchmaking_handler, HOST, MATCHMAKING_PORT):
        print(f"Game server on ws://{HOST}:{PORT}")
        print(f"Matchmaking server on ws://{HOST}:{MATCHMAKING_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
