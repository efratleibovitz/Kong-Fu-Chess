"""server/game/connection.py"""

import json
from urllib.parse import urlparse, parse_qs

from server.core.protocol import (
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
    Role,
)
from server.auth.service import get_user_id_by_token
from server.core.database import get_user_by_id
from server.core.game_logger import log_action
from server.core import redis_client as _rc
from server.game.session import get_session, register_session, GameSession
from server.game.rooms import create_room


def _piece_owner(piece) -> str:
    return COLOR_WHITE if piece.color.value == 'white' else COLOR_BLACK


async def game_handler(client_socket):
    """Direct-connect entry point (client_socket is a real websockets
    connection - used for local/dev runs without the WS Gateway in front).
    Kept as a thin wrapper so existing direct-connect tests/usage don't
    change; the actual logic lives in handle_client, which the shard's
    internal server (server/game/shard_app.py) also calls for
    Gateway-proxied clients, passing a RemoteClientSocket instead."""
    await handle_client(client_socket, client_socket.request.path)


async def handle_client(client_socket, path: str):
    """client_socket only needs to support: async send(str), async
    close(), and `async for raw in client_socket`. Real websockets
    connections satisfy this already; RemoteClientSocket (shard_app.py)
    is a proxy that satisfies it for Gateway-routed clients."""
    params = parse_qs(urlparse(path).query)
    room_id = params.get(QUERY_ROOM_ID, [None])[0]
    create = params.get(QUERY_CREATE, [None])[0] == FLAG_TRUE
    token = params.get(QUERY_TOKEN, [None])[0]

    user_id = get_user_id_by_token(token) if token else None
    if user_id is None:
        await client_socket.send(json.dumps(Message(MsgType.ERROR, {FIELD_REASON: Reason.UNAUTHORIZED.value}).to_dict()))
        await client_socket.close()
        return

    if create:
        if room_id and get_session(room_id) is not None:
            await client_socket.send(json.dumps(Message(MsgType.ERROR, {FIELD_REASON: Reason.ROOM_EXISTS.value}).to_dict()))
            await client_socket.close()
            return
        room_id = create_room(room_id)
    else:
        session = get_session(room_id)
        if session is None and room_id:
            # Shard may have restarted - attempt to restore from Redis snapshot.
            snapshot = await _rc.load_game_state(room_id)
            if snapshot is not None:
                session = GameSession.from_snapshot(snapshot)
                register_session(room_id, session)
        if not room_id or session is None:
            await client_socket.send(json.dumps(Message(MsgType.ERROR, {FIELD_REASON: Reason.INVALID_ROOM.value}).to_dict()))
            await client_socket.close()
            return

    session = get_session(room_id)
    connection = Connection(client_socket, session, user_id)
    await connection.run()


class Connection:
    def __init__(self, client_socket, session, user_id: int):
        self.client_socket = client_socket
        self.session = session
        self.user_id = user_id
        self.username = "unknown"
        self.color: str | None = None
        self.is_viewer = False
        self._role: Role | None = None
        self._handlers = {
            MsgType.CLICK: self._handle_click,
            MsgType.JUMP: self._handle_jump,
            MsgType.RESTART: self._handle_restart,
        }

    async def send(self, message: Message):
        await self.client_socket.send(json.dumps(message.to_dict()))

    async def send_raw(self, payload: str):
        await self.client_socket.send(payload)

    def _log(self, action: str, comment: str = "") -> None:
        log_action(self.session.room_id, self.user_id, self.username, self._role, action, comment)

    async def run(self):
        role = self.session.assign_color(self, self.user_id)
        if role is None:
            await self.send(Message(MsgType.ERROR, {FIELD_REASON: Reason.REJECTED.value}))
            await self.client_socket.close()
            return

        self._role = role
        if role is Role.VIEWER:
            self.is_viewer = True
        else:
            self.color = role.value
        user = get_user_by_id(self.user_id)
        self.username = user["username"] if user else "unknown"
        await self.send(Message(MsgType.ROLE, {"role": role.value}))
        self._log("connect")

        self.session.on_connect(self)
        await self.session.on_connected(self)
        try:
            async for raw in self.client_socket:
                await self._handle_message(raw)
        finally:
            self._log("disconnect")
            self.session.on_disconnect(self)

    async def _handle_message(self, raw: str):
        if self.is_viewer:
            return
        try:
            msg = Message.from_dict(json.loads(raw))
        except (json.JSONDecodeError, TypeError, KeyError, ValueError):
            return

        handler = self._handlers.get(msg.type)
        if handler:
            handler(msg)

    def _handle_restart(self, msg: dict):
        self.session.engine.restart()
        self._log("restart")

    def _handle_click(self, msg: dict):
        col, row = msg.get("col"), msg.get("row")
        if col is None or row is None:
            return
        if not self._click_is_allowed(col, row):
            return
        self.session.engine.click_cell(col, row, self.color)
        self._log("click", f"col={col}, row={row}")

    def _handle_jump(self, msg: dict):
        col, row = msg.get("col"), msg.get("row")
        if col is None or row is None:
            return
        from core.model.position import Position
        board = self.session.state.board
        pos = Position(col, row)
        if not board.is_within_bounds(pos):
            return
        piece = board.get_piece(pos)
        if piece is None or _piece_owner(piece) != self.color:
            return
        self.session.engine.jump_cell(col, row, self.color)
        self._log("jump", f"col={col}, row={row}")

    def _click_is_allowed(self, col: int, row: int) -> bool:
        from core.model.position import Position
        board = self.session.state.board
        pos = Position(col, row)
        if not board.is_within_bounds(pos):
            return False

        dest_piece = board.get_piece(pos)
        if dest_piece is not None and _piece_owner(dest_piece) == self.color:
            return True

        # click_cell only ever lets a color's slot hold that same color's
        # piece, so having a selection at all is enough to know it's mine
        return self.session.state.selected_by_color.get(self.color) is not None
