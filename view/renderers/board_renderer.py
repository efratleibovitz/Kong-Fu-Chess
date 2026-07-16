import time

import cv2
import numpy as np

from view.img import Img
from view.constants import CELL, GOLD, BOARD_IMG
from model.game_state import GameState
from input.board_mapper import BoardMapper
from view.loaders.sprite_loader import SpriteLoader



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

        cur_moving = {(m[1].col, m[1].row) for m in state.pending_moves}
        cur_jumping = {(j[1].col, j[1].row) for j in state.pending_jumps}

        for row_i, row in enumerate(state.board.rows):
            for col_i, token in enumerate(row):
                if token == '.':
                    continue
                piece_state = self._piece_state(token, cur_moving, cur_jumping, state, col_i, row_i)
                frames = self._loader.get(token, piece_state)
                if not frames:
                    continue
                key = f"{row_i}_{col_i}_{token}"
                idx = self._advance_frame(key, len(frames), dt, piece_state)
                frames[idx].draw_on(canvas, col_i * CELL, row_i * CELL)
                self._draw_cooldown_bar(canvas, col_i, row_i, state)

        # draw highlights on top of pieces
        if state.selected_position is not None:
            self._draw_highlight(canvas, state.selected_position.col,
                                 state.selected_position.row, (0, 215, 255))  # gold
        for move in state.pending_moves:
            self._draw_highlight(canvas, move[2].col, move[2].row, (0, 120, 255))  # orange

    def _piece_state(self, token: str, moving: set, jumping: set, state: GameState, col: int, row: int) -> str:
        if (col, row) in moving:
            return 'move'
        if (col, row) in jumping:
            return 'jump'
        key = (col, row)
        expire = state.cooldowns.get(key)
        if expire and expire > state.clock:
            return state.rest_type.get(key, 'long_rest')
        return 'idle'

    def _advance_frame(self, key: str, total: int, dt: float, piece_state: str) -> int:
        fps = {'move': 12, 'jump': 10, 'long_rest': 6, 'short_rest': 8}.get(piece_state, 6)
        self._frame_counters.setdefault(key, 0.0)
        self._frame_counters[key] = (self._frame_counters[key] + dt * fps) % total
        return int(self._frame_counters[key])

    def _draw_cooldown_bar(self, canvas: Img, col: int, row: int, state: GameState):
        key = (col, row)
        expire = state.cooldowns.get(key)
        if not expire or expire <= state.clock:
            return
        rest = state.rest_type.get(key, 'long_rest')
        total_ms = 2000 if rest == 'long_rest' else 1000
        remaining = expire - state.clock
        fill = max(0.0, min(1.0, remaining / total_ms))
        color = (0, 120, 255) if rest == 'long_rest' else (255, 160, 0)
        x = col * CELL + 6
        y = row * CELL + CELL - 8
        bar_w = CELL - 12
        bar_h = 5
        cv2.rectangle(canvas.img, (x, y), (x + bar_w, y + bar_h), (50, 50, 50), -1)
        cv2.rectangle(canvas.img, (x, y), (x + int(bar_w * fill), y + bar_h), color, -1)

    def _draw_highlight(self, canvas: Img, col: int, row: int, color_bgr: tuple):
        x, y = col * CELL, row * CELL
        for i in range(6):
            alpha = 0.6 - i * 0.1
            thickness = i + 1
            overlay = canvas.img.copy()
            cv2.rectangle(overlay, (x + i, y + i),
                          (x + CELL - i, y + CELL - i), color_bgr, thickness)
            cv2.addWeighted(overlay, alpha, canvas.img, 1 - alpha, 0, canvas.img)
