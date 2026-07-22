import json
from urllib.parse import quote
import websockets.sync.client

from server.auth.service import login_with_session, register
from client.network_client import NetworkClient, log_sent, log_received
from client.network_session import NetworkSession
from view.screen import Screen
from view.menu_screen import MenuScreen
from server.core.protocol import (
    HOST,
    PORT,
    MATCHMAKING_PORT,
    COLOR_WHITE,
    COLOR_BLACK,
    MSG_TYPE_MATCH_FOUND,
    MSG_TYPE_ERROR,
    MSG_TYPE_ROLE,
    MSG_TYPE_WAITING,
    QUERY_ROOM_ID,
    QUERY_TOKEN,
    QUERY_CREATE,
    FLAG_TRUE,
    FIELD_REASON,
    Reason,
)

MATCHMAKING_URL = f"ws://{HOST}:{MATCHMAKING_PORT}"
GAME_URL = f"ws://{HOST}:{PORT}"


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
    with websockets.sync.client.connect(f"{MATCHMAKING_URL}?{QUERY_TOKEN}={token}") as ws:
        for raw in ws:
            msg = json.loads(raw)
            log_received(msg)
            if msg.get("type") == MSG_TYPE_MATCH_FOUND:
                return msg
            if msg.get("type") == MSG_TYPE_ERROR:
                raise RuntimeError(msg.get(FIELD_REASON))


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
            msg = json.loads(raw)
            log_received(msg)
            msg_type = msg.get("type")
            if msg_type == MSG_TYPE_ROLE:
                role = msg["role"]
            elif msg_type == MSG_TYPE_WAITING:
                room_id = msg.get(QUERY_ROOM_ID)
            elif msg_type == MSG_TYPE_ERROR:
                raise RuntimeError(msg.get(FIELD_REASON))
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


_ERROR_MESSAGES = {
    Reason.ROOM_EXISTS.value: "That room name is already taken - try another.",
    Reason.INVALID_ROOM.value: "That room doesn't exist - check the code and try again.",
    Reason.UNAUTHORIZED.value: "Authorization failed - please log in again.",
    Reason.TIMEOUT.value: "No match found in time - please try again.",
    Reason.REJECTED.value: "That room is already full.",
}


def _friendly_error(reason) -> str:
    return _ERROR_MESSAGES.get(reason, f"Error: {reason}")


def main():
    token = _get_token()

    while True:
        action, room_code = MenuScreen().run()
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
        except RuntimeError as e:
            print(_friendly_error(str(e)))
            continue
        break

    print(f"Connected as {_role_label(role)}.")
    client = NetworkClient(f"{GAME_URL}?{QUERY_ROOM_ID}={quote(room_id, safe='')}&{QUERY_TOKEN}={token}")
    client.start()

    session = NetworkSession(client, role)
    Screen(session, session, window_title=f"Kong-Fu Chess - {_role_label(role)}").run()


if __name__ == "__main__":
    main()
