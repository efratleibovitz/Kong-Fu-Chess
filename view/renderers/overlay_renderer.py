import pathlib
import sys

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "CTD26" / "py"))
from img import Img

from model.game_state import GameState

BOARD_IMG = pathlib.Path(__file__).parent.parent / "CTD26" / "board.png"
GOLD = (0, 215, 255)
WHITE = (255, 255, 255)
RED = (0, 0, 255)


class OverlayRenderer:
    def __init__(self, w: int, h: int):
        self._w = w
        self._h = h
        self._bg = Img().read(str(BOARD_IMG), size=(w, h))

    def draw_start(self, canvas: Img):
        self._draw_dimmed_bg(canvas)
        cx = self._w // 2
        cy = self._h // 2
        canvas.put_text("KONG-FU CHESS", cx - 200, cy - 60, 1.8, GOLD + (255,), 3)
        canvas.put_text("Click to start", cx - 100, cy + 20, 1.0, WHITE + (255,), 2)

    def draw_win(self, canvas: Img, state: GameState):
        self._draw_dimmed_bg(canvas)
        cx = self._w // 2
        cy = self._h // 2
        canvas.put_text("GAME OVER", cx - 160, cy - 60, 2.0, RED + (255,), 4)
        if state.loser is not None:
            winner = 'w' if state.loser == 'b' else 'b'
            winner_name = state.player_names[winner]
            score = state.scores[winner]
            canvas.put_text(f"{winner_name} wins!", cx - 120, cy + 10, 1.4, GOLD + (255,), 3)
            canvas.put_text(f"Score: {score}", cx - 70, cy + 60, 1.0, WHITE + (255,), 2)
        canvas.put_text("Press Q to quit", cx - 110, cy + 110, 0.8, WHITE + (255,), 1)

    def _draw_dimmed_bg(self, canvas: Img):
        self._bg.draw_on(canvas, 0, 0)
        dim = np.zeros((self._h, self._w, 3), dtype=np.uint8)
        cv2.addWeighted(dim, 0.6, canvas.img, 0.4, 0, canvas.img)
