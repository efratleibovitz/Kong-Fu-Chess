"""server/game/connection.py"""

import json
from urllib.parse import urlparse, parse_qs

from server.core.protocol import (
    COLOR_WHITE,
    COLOR_BLACK,
    MSG_TYPE_CLICK,
    MSG_TYPE_JUMP,
    MSG_TYPE_RESTART,
    MSG_TYPE_ERROR,
    MSG_TYPE_ROLE,
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
from server.game.session import get_session
from server.game.rooms import create_room


def _piece_owner(piece) -> str:
    return COLOR_WHITE if piece.color.value == 'white' else COLOR_BLACK


async def game_handler(websocket):
    params = parse_qs(urlparse(websocket.request.path).query)
    room_id = params.get(QUERY_ROOM_ID, [None])[0]
    create = params.get(QUERY_CREATE, [None])[0] == FLAG_TRUE
    token = params.get(QUERY_TOKEN, [None])[0]

    user_id = get_user_id_by_token(token) if token else None
    if user_id is None:
        await websocket.send(json.dumps({"type": MSG_TYPE_ERROR, FIELD_REASON: Reason.UNAUTHORIZED.value}))
        await websocket.close()
        return

    if create:
        if room_id and get_session(room_id) is not None:
            await websocket.send(json.dumps({"type": MSG_TYPE_ERROR, FIELD_REASON: Reason.ROOM_EXISTS.value}))
            await websocket.close()
            return
        room_id = create_room(room_id)
    elif not room_id or get_session(room_id) is None:
        await websocket.send(json.dumps({"type": MSG_TYPE_ERROR, FIELD_REASON: Reason.INVALID_ROOM.value}))
        await websocket.close()
        return

    session = get_session(room_id)
    connection = Connection(websocket, session, user_id)
    await connection.run()


class Connection:
    def __init__(self, websocket, session, user_id: int):
        self.websocket = websocket
        self.session = session
        self.user_id = user_id
        self.username = "unknown"
        self.color: str | None = None
        self.is_viewer = False
        self._role: Role | None = None

    async def send(self, message: dict):
        await self.websocket.send(json.dumps(message))

    async def send_raw(self, payload: str):
        await self.websocket.send(payload)

    def _log(self, action: str, comment: str = "") -> None:
        log_action(self.session.room_id, self.user_id, self.username, self._role, action, comment)

    async def run(self):
        role = self.session.assign_color(self, self.user_id)
        if role is None:
            await self.send({"type": MSG_TYPE_ERROR, FIELD_REASON: Reason.REJECTED.value})
            await self.websocket.close()
            return

        self._role = role
        if role is Role.VIEWER:
            self.is_viewer = True
        else:
            self.color = role.value
        user = get_user_by_id(self.user_id)
        self.username = user["username"] if user else "unknown"
        await self.send({"type": MSG_TYPE_ROLE, "role": role.value})
        self._log("connect")

        self.session.on_connect(self)
        await self.session.on_connected(self)
        try:
            async for raw in self.websocket:
                await self._handle_message(raw)
        finally:
            self._log("disconnect")
            self.session.on_disconnect(self)

    async def _handle_message(self, raw: str):
        if self.is_viewer:
            return
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return

        msg_type = msg.get("type")

        if msg_type == MSG_TYPE_CLICK:
            self._handle_click(msg)
        elif msg_type == MSG_TYPE_JUMP:
            self._handle_jump(msg)
        elif msg_type == MSG_TYPE_RESTART:
            self.session.engine.restart()
            self._log("restart")

    def _handle_click(self, msg: dict):
        col, row = msg.get("col"), msg.get("row")
        if col is None or row is None:
            return
        if not self._click_is_allowed(col, row):
            return
        self.session.engine.click_cell(col, row)
        self._log("click", f"col={col}, row={row}")

    def _handle_jump(self, msg: dict):
        col, row = msg.get("col"), msg.get("row")
        if col is None or row is None:
            return
        from model.position import Position
        board = self.session.state.board
        pos = Position(col, row)
        if not board.is_within_bounds(pos):
            return
        piece = board.get_piece(pos)
        if piece is None or _piece_owner(piece) != self.color:
            return
        self.session.engine.jump_cell(col, row)
        self._log("jump", f"col={col}, row={row}")

    def _click_is_allowed(self, col: int, row: int) -> bool:
        from model.position import Position
        board = self.session.state.board
        pos = Position(col, row)
        if not board.is_within_bounds(pos):
            return False

        dest_piece = board.get_piece(pos)
        if dest_piece is not None and _piece_owner(dest_piece) == self.color:
            return True

        selected = self.session.state.selected_position
        if selected is not None:
            selected_piece = board.get_piece(selected)
            if selected_piece is not None and _piece_owner(selected_piece) == self.color:
                return True

        return False
