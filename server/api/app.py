"""server/api/app.py

API Gateway (Server_Design.md Sec.1). REST only - non-real-time traffic:
register, login, rooms, history. Never touches game state or the
GameEngine; wraps the existing server/auth/service.py logic behind HTTP
instead of client code importing it directly.

/rooms and /history are honest stubs, not fake data: listing active rooms
across shards needs a shared registry (Redis, per Server_Design.md Sec.4
Q2) that doesn't exist yet, and there's no `games`/move-history table in
Postgres yet either - both are real next steps, not implemented here.
"""

import os

from aiohttp import web

from server.core.database import init_db
from server.auth.service import register, login_with_session

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("API_PORT", "8000"))


async def handle_register(request: web.Request) -> web.Response:
    body = await request.json()
    username, password = body.get("username"), body.get("password")
    if not username or not password:
        return web.json_response({"error": "username and password required"}, status=400)
    try:
        user_id = register(username, password)
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=409)
    return web.json_response({"user_id": user_id}, status=201)


async def handle_login(request: web.Request) -> web.Response:
    body = await request.json()
    username, password = body.get("username"), body.get("password")
    result = login_with_session(username, password) if username and password else None
    if result is None:
        return web.json_response({"error": "invalid credentials"}, status=401)
    user_id, token = result
    return web.json_response({"user_id": user_id, "token": token})


async def handle_rooms(request: web.Request) -> web.Response:
    return web.json_response({"rooms": [], "note": "not implemented in MVP - needs a Redis room registry shared across shards"})


async def handle_history(request: web.Request) -> web.Response:
    return web.json_response({"games": [], "note": "not implemented in MVP - needs a games/move-history table"})


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/register", handle_register)
    app.router.add_post("/login", handle_login)
    app.router.add_get("/rooms", handle_rooms)
    app.router.add_get("/history/{user_id}", handle_history)
    app.router.add_get("/health", handle_health)
    return app


def main():
    init_db()
    web.run_app(build_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
