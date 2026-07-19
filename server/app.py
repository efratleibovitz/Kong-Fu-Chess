# import asyncio
# import json
# import websockets
# from server.game_session import GameSession
# from server.connection import Connection

# _session = GameSession()


# async def handler(websocket):
#     if _session.is_full():
#         await websocket.send(json.dumps({"type": "error", "reason": "room_full"}))
#         await websocket.close()
#         return

#     conn = Connection(websocket, _session)
#     await conn.run()


# async def main():
#     print("Server listening on ws://localhost:8765")
#     async with websockets.serve(handler, "localhost", 8765):
#         await asyncio.Future()  # run forever


# if __name__ == "__main__":
#     asyncio.run(main())


"""server/app.py"""

import asyncio
import json
import websockets

from server.game_session import GameSession
from server.connection import Connection

HOST = "localhost"
PORT = 8765


async def handler(websocket, session: GameSession):
    if session.is_full():
        await websocket.send(json.dumps({"type": "error", "reason": "room_full"}))
        await websocket.close()
        return

    connection = Connection(websocket, session)
    await connection.run()


async def main():
    session = GameSession()

    async def bound_handler(websocket):
        await handler(websocket, session)

    async with websockets.serve(bound_handler, HOST, PORT):
        print(f"Kung Fu Chess server listening on ws://{HOST}:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())