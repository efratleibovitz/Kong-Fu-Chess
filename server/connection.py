"""server/connection.py"""

import json


def _piece_owner(piece) -> str:
    return 'w' if piece.color.value == 'white' else 'b'


class Connection:
    def __init__(self, websocket, session):
        self.websocket = websocket
        self.session = session
        self.color: str | None = None

    async def send(self, message: dict):
        await self.websocket.send(json.dumps(message))

    async def send_raw(self, payload: str):
        await self.websocket.send(payload)

    async def run(self):
        self.color = self.session.assign_color(self)
        await self.session.on_connected(self)
        try:
            async for raw in self.websocket:
                await self._handle_message(raw)
        finally:
            self.session.remove(self)

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return

        msg_type = msg.get("type")

        if msg_type == "click":
            self._handle_click(msg)
        elif msg_type == "jump":
            self._handle_jump(msg)
        elif msg_type == "restart":
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
    
    