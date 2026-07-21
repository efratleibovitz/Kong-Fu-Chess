"""client/network_session.py

Passed to view.screen.Screen as BOTH `engine` and `state` - Screen calls
self._engine.wait/click/jump/restart and self._state.board/events/
to_render_state()/clock/cooldowns/rest_type, and those two sets of names
never overlap, so one object can satisfy both roles. Screen itself is not
touched and has no idea it isn't talking to a local GameEngine/GameState.

wait() emits a redraw event on every call (not only when a new server
message arrived), so Screen always takes its `if self._needs_redraw`
branch and rebuilds straight from to_render_state(). That keeps Screen's
_update_cooldown_fills path (the elif branch) from ever running here -
cooldown_fill stays exactly what the server sent, no local interpolation.
cooldowns/rest_type are kept permanently empty since nothing reads them.
"""

import types

from model.event_bus import EventBus
from view.render_state import RenderState, PieceRenderInfo, MoveArrow
from input.board_mapper import BoardMapper
from client.network_client import NetworkClient
from client.render_state_codec import render_state_from_dict

NUM_COLS = 8
NUM_ROWS = 8


def _flip_render_state(rs: RenderState) -> RenderState:
    rs.pieces = [
        PieceRenderInfo(
            token=p.token,
            col=7 - p.col,
            row=7 - p.row,
            state=p.state,
            cooldown_fill=p.cooldown_fill,
            cooldown_is_long=p.cooldown_is_long,
        )
        for p in rs.pieces
    ]
    rs.selected_col = 7 - rs.selected_col if rs.selected_col is not None else None
    rs.selected_row = 7 - rs.selected_row if rs.selected_row is not None else None
    rs.pending_destinations = [
        MoveArrow(to_col=7 - a.to_col, to_row=7 - a.to_row)
        for a in rs.pending_destinations
    ]
    return rs


class NetworkSession:
    def __init__(self, client: NetworkClient, color: str):
        self._client = client
        self._color = color
        self.board = types.SimpleNamespace(num_cols=NUM_COLS, num_rows=NUM_ROWS)
        self.events = EventBus()
        self.clock = 0
        self.cooldowns: dict = {}
        self.rest_type: dict = {}
        self._rs: RenderState | None = None

    # --- state role ---

    def to_render_state(self) -> RenderState:
        return self._rs

    # --- engine role ---

    def wait(self, ms: int):
        for msg in self._client.poll():
            self._handle_message(msg)
        self.events.emit('piece_settled')

    def click(self, x: int, y: int):
        self._send(x, y, self._client.send_click)

    def jump(self, x: int, y: int):
        self._send(x, y, self._client.send_jump)

    def restart(self):
        self._client.send_restart()

    # --- internals ---

    def _send(self, x: int, y: int, send_fn):
        if not BoardMapper.is_within_bounds(x, y, NUM_COLS, NUM_ROWS):
            return
        pos = BoardMapper.pixel_to_cell(x, y)
        col, row = pos.col, pos.row
        if self._color == 'b':
            col, row = 7 - col, 7 - row
        send_fn(col, row)

    def _handle_message(self, msg: dict):
        t = msg.get("type")
        if t == "state":
            rs = render_state_from_dict(msg["data"])
            if self._color == 'b':
                rs = _flip_render_state(rs)
            self._rs = rs
            self.clock = rs.clock_ms
        elif t == "game_over":
            if self._rs is not None:
                self._rs.game_over = True
                self._rs.loser = msg.get("loser")
