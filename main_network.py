import json
import websockets.sync.client

from server.auth import login_with_session, register
from client.network_client import NetworkClient
from client.network_session import NetworkSession
from view.screen import Screen
from protocol import COLOR_WHITE, MSG_TYPE_MATCH_FOUND, MSG_TYPE_ERROR

MATCHMAKING_URL = "ws://localhost:8766"
GAME_URL = "ws://localhost:8765"


def _get_token() -> str:
    while True:
        print("\n[1] Register  [2] Login")
        choice = input("> ").strip()
        username = input("Username: ").strip()
        password = input("Password: ").strip()

        if choice == "1":
            try:
                register(username, password)
            except ValueError as e:
                print(f"Error: {e}")
                continue

        result = login_with_session(username, password)
        if result is None:
            print("Invalid username or password.")
            continue
        _user_id, token = result
        return token


def _connect_matchmaking(token: str) -> dict:
    """Blocking one-shot connect: sits on the socket until match_found."""
    with websockets.sync.client.connect(f"{MATCHMAKING_URL}?token={token}") as ws:
        for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == MSG_TYPE_MATCH_FOUND:
                return msg
            if msg.get("type") == MSG_TYPE_ERROR:
                raise RuntimeError(f"matchmaking error: {msg.get('reason')}")


def main():
    token = _get_token()

    print("Looking for an opponent...")
    match = _connect_matchmaking(token)
    color = match["color"]
    room_id = match["room_id"]

    print(f"Match found. Playing as {'White' if color == COLOR_WHITE else 'Black'}.")
    client = NetworkClient(f"{GAME_URL}?room_id={room_id}&token={token}")
    client.start()

    session = NetworkSession(client, color)
    Screen(session, session).run()


if __name__ == "__main__":
    main()
