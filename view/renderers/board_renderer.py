import time

import cv2
import numpy as np

from view.img import Img
from view.constants import CELL, GOLD, BOARD_IMG, PieceState
from view.render_state import RenderState
from view.loaders.sprite_loader import SpriteLoader


class BoardRenderer:
    def __init__(self, loader: SpriteLoader):
        self._loader = loader
        self._board_img = Img().read(str(BOARD_IMG), size=(8 * CELL, 8 * CELL))
        self._frame_counters: dict[str, float] = {}
        self._last_tick = time.time()

    def render(self, canvas: Img, rs: RenderState):
        self._board_img.draw_on(canvas, 0, 0)

        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        for piece in rs.pieces:
            frames = self._loader.get(piece.token, piece.state)
            if not frames:
                continue
            key = f"{piece.row}_{piece.col}_{piece.token}"
            idx = self._advance_frame(key, len(frames), dt, piece.state)
            frames[idx].draw_on(canvas, piece.col * CELL, piece.row * CELL)
            if piece.cooldown_fill > 0:
                self._draw_cooldown_bar(canvas, piece.col, piece.row, piece.cooldown_fill, piece.cooldown_is_long)

        if rs.selected_col is not None:
            self._draw_highlight(canvas, rs.selected_col, rs.selected_row, (0, 215, 255))
        for arrow in rs.pending_destinations:
            self._draw_highlight(canvas, arrow.to_col, arrow.to_row, (0, 120, 255))

    def _advance_frame(self, key: str, total: int, dt: float, piece_state: PieceState) -> int:
        fps = {
            PieceState.MOVE: 12, PieceState.JUMP: 10,
            PieceState.LONG_REST: 6, PieceState.SHORT_REST: 8
        }.get(piece_state, 6)
        self._frame_counters.setdefault(key, 0.0)
        self._frame_counters[key] = (self._frame_counters[key] + dt * fps) % total
        return int(self._frame_counters[key])

    def _draw_cooldown_bar(self, canvas: Img, col: int, row: int, fill: float, is_long: bool):
        color = (0, 120, 255) if is_long else (255, 160, 0)
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
            overlay = canvas.img.copy()
            cv2.rectangle(overlay, (x + i, y + i),
                          (x + CELL - i, y + CELL - i), color_bgr, i + 1)
            cv2.addWeighted(overlay, alpha, canvas.img, 1 - alpha, 0, canvas.img)
