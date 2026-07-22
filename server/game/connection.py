"""server/game/connection.py"""

import json
from urllib.parse import urlparse, parse_qs

from server.core.protocol import COLOR_WHITE, COLOR_BLACK, MSG_TYPE_CLICK, MSG_TYPE_JUMP, MSG_TYPE_RESTART, MSG_TYPE_ERROR
from server.auth.service import get_user_id_by_token
from server.game.session import get_session


def _piece_owner(piece) -> str:
    return COLOR_WHITE if piece.color.value == 'white' else COLOR_BLACK


async def game_handler(websocket):
    params = parse_qs(urlparse(websocket.request.path).query)
    room_id = params.get("room_id", [None])[0]
    token = params.get("token", [None])[0]

    session = get_session(room_id) if room_id else None
    if session is None:
        await websocket.send(json.dumps({"type": MSG_TYPE_ERROR, "reason": "invalid_room"}))
        await websocket.close()
        return

    user_id = get_user_id_by_token(token) if token else None
    if user_id is None:
        await websocket.send(json.dumps({"type": MSG_TYPE_ERROR, "reason": "unauthorized"}))
        await websocket.close()
        return

    connection = Connection(websocket, session, user_id)
    await connection.run()


class Connection:
    def __init__(self, websocket, session, user_id: int):
        self.websocket = websocket
        self.session = session
        self.user_id = user_id
        self.color: str | None = None

    async def send(self, message: dict):
        await self.websocket.send(json.dumps(message))

    async def send_raw(self, payload: str):
        await self.websocket.send(payload)

    async def run(self):
        self.color = self.session.assign_color(self, self.user_id)
        if self.color is None:
            await self.send({"type": MSG_TYPE_ERROR, "reason": "rejected"})
            await self.websocket.close()
            return

        self.session.on_connect(self)
        await self.session.on_connected(self)
        try:
            async for raw in self.websocket:
                await self._handle_message(raw)
        finally:
            self.session.on_disconnect(self)

    async def _handle_message(self, raw: str):
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

    def _handle_click(self, msg: dict):
        col, row = msg.get("col"), msg.get("row")
        if col is None or row is None:
            return
        if not self._click_is_allowed(col, row):
            return
        self.session.engine.click_cell(col, row)

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
