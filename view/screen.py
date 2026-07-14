import pathlib
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent / "CTD26" / "py"))
from img import Img

from engine.game_engine import GameEngine
from model.game_state import GameState
from input.board_mapper import BoardMapper
from view.sprite_loader import SpriteLoader
from view.board_renderer import BoardRenderer

CELL = BoardMapper.CELL_SIZE
FPS = 30
WINDOW = "Kong-Fu Chess"


class Screen:
    def __init__(self, engine: GameEngine, state: GameState):
        self._engine = engine
        self._state = state
        loader = SpriteLoader()
        self._board_renderer = BoardRenderer(loader)
        cols = state.board.num_cols
        rows = state.board.num_rows
        self._w = cols * CELL
        self._h = rows * CELL
        self._last_right_click: tuple[int, int] | None = None

    def run(self):
        cv2.namedWindow(WINDOW)
        cv2.setMouseCallback(WINDOW, self._on_mouse)
        frame_ms = int(1000 / FPS)

        while True:
            canvas = self._make_canvas()
            self._board_renderer.render(canvas, self._state)

            if self._state.game_over:
                canvas.put_text("GAME OVER", self._w // 4, self._h // 2,
                                2.0, (0, 0, 255, 255), 4)

            cv2.imshow(WINDOW, canvas.img)
            key = cv2.waitKey(frame_ms) & 0xFF
            if key == ord('q') or key == 27:
                break

            tick_ms = frame_ms
            self._engine.wait(tick_ms)

        cv2.destroyAllWindows()

    def _make_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.zeros((self._h, self._w, 3), dtype=np.uint8)
        canvas.img[:] = (30, 30, 30)
        return canvas

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self._engine.click(x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            self._engine.jump(x, y)
