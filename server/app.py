"""server/app.py"""

import asyncio
import json
import websockets
from urllib.parse import urlparse, parse_qs

from server.game_session import GameSession
from server.connection import Connection
from server.auth import get_user_id_by_token
from server.db import get_user_by_id, init_db
from server.matchmaking import add_to_queue

HOST = "localhost"
PORT = 8765
MATCHMAKING_PORT = 8766


async def handler(websocket, session: GameSession):
    if session.is_full():
        await websocket.send(json.dumps({"type": "error", "reason": "room_full"}))
        await websocket.close()
        return

    connection = Connection(websocket, session)
    await connection.run()


async def matchmaking_handler(websocket):
    params = parse_qs(urlparse(websocket.path).query)
    token = params.get("token", [None])[0]

    user_id = get_user_id_by_token(token) if token else None
    if user_id is None:
        await websocket.send(json.dumps({"type": "error", "reason": "unauthorized"}))
        await websocket.close()
        return

    user = get_user_by_id(user_id)
    elo = user["elo"]

    await add_to_queue(websocket, user_id, elo)


async def main():
    init_db()
    session = GameSession()

    async def bound_handler(websocket):
        await handler(websocket, session)

    async with websockets.serve(bound_handler, HOST, PORT), \
                websockets.serve(matchmaking_handler, HOST, MATCHMAKING_PORT):
        print(f"Game server on ws://{HOST}:{PORT}")
        print(f"Matchmaking server on ws://{HOST}:{MATCHMAKING_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())