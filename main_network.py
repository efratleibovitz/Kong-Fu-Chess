import json
import urllib.request
from urllib.parse import quote
import websockets.sync.client

from client.network_client import NetworkClient, log_sent, log_received
from client.network_session import NetworkSession
from client.errors import ServerError
from view.screen import Screen
from view.menu_screen import MenuScreen
from server.core.protocol import (
    HOST,
    PORT,
    MATCHMAKING_PORT,
    COLOR_WHITE,
    COLOR_BLACK,
    MsgType,
    Message,
    QUERY_ROOM_ID,
    QUERY_TOKEN,
    QUERY_CREATE,
    FLAG_TRUE,
    FIELD_REASON,
    Reason,
)

MATCHMAKING_URL = f"ws://{HOST}:{MATCHMAKING_PORT}"
GAME_URL = f"ws://{HOST}:{PORT}"
API_URL = f"http://{HOST}:8000"


def _api_post(path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API_URL}{path}", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _get_token() -> str:
    while True:
        print("\n[1] Register  [2] Login")
        choice = input("> ").strip()
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        payload = {"username": username, "password": password}

        if choice == "1":
            status, resp = _api_post("/register", payload)
            if status != 201:
                print(f"Error: {resp.get('error', 'registration failed')}")
                continue

        status, resp = _api_post("/login", payload)
        if status != 200:
            print("Invalid username or password.")
            continue
        return resp["token"]


def _connect_matchmaking(token: str) -> Message:
    """Blocking one-shot connect: sits on the socket until match_found."""
    with websockets.sync.client.connect(f"{MATCHMAKING_URL}?{QUERY_TOKEN}={token}") as ws:
        for raw in ws:
            data = json.loads(raw)
            log_received(data)
            msg = Message.from_dict(data)
            if msg.type is MsgType.MATCH_FOUND:
                return msg
            if msg.type is MsgType.ERROR:
                raise ServerError(Reason(msg.get(FIELD_REASON)))


def _peek_role(url: str, need_room_id: bool) -> tuple[str, str | None]:
    """Open a throwaway sync connection to the game port just long enough to
    learn the role the server assigned (and, for a freshly created room,
    its room_id from the 'waiting' message), then close it. The persistent
    NetworkClient connection opened right after reconnects on the same
    room_id/token - Stage D's identity-based reconnect/grace logic already
    handles that handoff correctly, so no special-casing is needed here."""
    role = None
    room_id = None
    with websockets.sync.client.connect(url) as ws:
        for raw in ws:
            data = json.loads(raw)
            log_received(data)
            msg = Message.from_dict(data)
            if msg.type is MsgType.ROLE:
                role = msg["role"]
            elif msg.type is MsgType.WAITING:
                room_id = msg.get(QUERY_ROOM_ID)
            elif msg.type is MsgType.ERROR:
                raise ServerError(Reason(msg.get(FIELD_REASON)))
            if role is not None and (not need_room_id or room_id is not None):
                break
    return role, room_id


def _create_room(token: str, room_code: str | None = None) -> tuple[str, str]:
    url = f"{GAME_URL}?{QUERY_CREATE}={FLAG_TRUE}&{QUERY_TOKEN}={token}"
    if room_code:
        url += f"&{QUERY_ROOM_ID}={quote(room_code, safe='')}"
    role, room_id = _peek_role(url, need_room_id=True)
    return role, room_id


def _join_room(room_id: str, token: str) -> str:
    url = f"{GAME_URL}?{QUERY_ROOM_ID}={quote(room_id, safe='')}&{QUERY_TOKEN}={token}"
    role, _ = _peek_role(url, need_room_id=False)
    return role


def _role_label(role: str) -> str:
    if role == COLOR_WHITE:
        return "White"
    if role == COLOR_BLACK:
        return "Black"
    return "Viewer"


def main():
    token = _get_token()

    error = None
    while True:
        action, room_code = MenuScreen(error=error).run()
        error = None
        if action == "quit":
            return

        try:
            if action == "create":
                role, room_id = _create_room(token, room_code)
                print(f"Room created. Share this Room ID with your opponent: {room_id}")
            elif action == "join":
                room_id = room_code
                role = _join_room(room_id, token)
            else:
                print("Looking for an opponent...")
                match = _connect_matchmaking(token)
                role = match["color"]
                room_id = match[QUERY_ROOM_ID]
        except ServerError as e:
            error = e.friendly_message
            continue
        break

    print(f"Connected as {_role_label(role)}.")
    client = NetworkClient(f"{GAME_URL}?{QUERY_ROOM_ID}={quote(room_id, safe='')}&{QUERY_TOKEN}={token}")
    client.start()

    session = NetworkSession(client, role)
    Screen(session, session, window_title=f"Kong-Fu Chess - {_role_label(role)}").run()


if __name__ == "__main__":
    main()
