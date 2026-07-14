import pathlib
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent / "CTD26" / "py"))
from img import Img

from model.game_state import GameState
from input.board_mapper import BoardMapper
from view.sprite_loader import SpriteLoader, CELL

BOARD_IMG = pathlib.Path(__file__).parent / "CTD26" / "board.png"
CELL = BoardMapper.CELL_SIZE


# rest duration constants — must match MoveSettler
_LONG_REST_MS = 1500
_SHORT_REST_MS = 600


class BoardRenderer:
    def __init__(self, loader: SpriteLoader):
        self._loader = loader
        self._board_img = Img().read(str(BOARD_IMG), size=(8 * CELL, 8 * CELL))
        self._frame_counters: dict[str, float] = {}
        self._last_tick = time.time()

    def render(self, canvas: Img, state: GameState):
        self._board_img.draw_on(canvas, 0, 0)

        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        cur_moving = {m[0] for m in state.pending_moves}
        cur_jumping = {j[0] for j in state.pending_jumps}

        for row_i, row in enumerate(state.board.rows):
            for col_i, token in enumerate(row):
                if token == '.':
                    continue
                piece_state = self._piece_state(token, cur_moving, cur_jumping, state)
                frames = self._loader.get(token, piece_state)
                if not frames:
                    continue
                key = f"{row_i}_{col_i}_{token}"
                idx = self._advance_frame(key, len(frames), dt, piece_state)
                frames[idx].draw_on(canvas, col_i * CELL, row_i * CELL)

        # draw highlights on top of pieces
        if state.selected_position is not None:
            self._draw_highlight(canvas, state.selected_position.col,
                                 state.selected_position.row, (0, 215, 255))  # gold
        for move in state.pending_moves:
            self._draw_highlight(canvas, move[2].col, move[2].row, (0, 120, 255))  # orange

    def _piece_state(self, token: str, moving: set, jumping: set, state: GameState) -> str:
        if token in moving:
            return 'move'
        if token in jumping:
            return 'jump'
        expire = state.cooldowns.get(token)
        if expire and expire > state.clock:
            remaining = expire - state.clock
            return 'long_rest' if remaining > _SHORT_REST_MS else 'short_rest'
        return 'idle'

    def _advance_frame(self, key: str, total: int, dt: float, piece_state: str) -> int:
        fps = {'move': 12, 'jump': 10, 'long_rest': 6, 'short_rest': 8}.get(piece_state, 6)
        self._frame_counters.setdefault(key, 0.0)
        self._frame_counters[key] = (self._frame_counters[key] + dt * fps) % total
        return int(self._frame_counters[key])

    def _draw_highlight(self, canvas: Img, col: int, row: int, color_bgr: tuple):
        x, y = col * CELL, row * CELL
        for i in range(6):
            alpha = 0.6 - i * 0.1
            thickness = i + 1
            overlay = canvas.img.copy()
            cv2.rectangle(overlay, (x + i, y + i),
                          (x + CELL - i, y + CELL - i), color_bgr, thickness)
            cv2.addWeighted(overlay, alpha, canvas.img, 1 - alpha, 0, canvas.img)
