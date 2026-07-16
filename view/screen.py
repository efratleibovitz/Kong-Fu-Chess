import cv2
import numpy as np

from view.img import Img
from view.constants import CELL, HUD_W, FPS
from engine.game_engine import GameEngine
from model.game_state import GameState
from view.loaders.sprite_loader import SpriteLoader
from view.renderers.board_renderer import BoardRenderer
from view.renderers.hud_renderer import HUDRenderer
from view.renderers.overlay_renderer import OverlayRenderer

WINDOW = "Kong-Fu Chess"


class Screen:
    def __init__(self, engine: GameEngine, state: GameState):
        self._engine = engine
        self._state = state
        loader = SpriteLoader()
        self._board_renderer = BoardRenderer(loader)
        self._hud_renderer = HUDRenderer(loader, state.board.num_rows * CELL)
        self._board_w = state.board.num_cols * CELL
        self._board_h = state.board.num_rows * CELL
        self._total_w = self._board_w + HUD_W
        self._overlay = OverlayRenderer(self._board_w, self._board_h)
        self._started = False

    def run(self):
        cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
        cv2.setWindowProperty(WINDOW, cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback(WINDOW, self._on_mouse)
        frame_ms = int(1000 / FPS)

        while True:
            canvas = self._make_canvas()
            board_canvas = self._make_board_canvas()

            if not self._started:
                self._overlay.draw_start(board_canvas)
                board_canvas.draw_on(canvas, 0, 0)
            else:
                self._board_renderer.render(board_canvas, self._state)
                board_canvas.draw_on(canvas, 0, 0)
                hud = self._hud_renderer.make_panel(self._state)
                hud.draw_on(canvas, self._board_w, 0)
                if self._state.game_over:
                    win_canvas = self._make_board_canvas()
                    self._overlay.draw_win(win_canvas, self._state)
                    win_canvas.draw_on(canvas, 0, 0)

            cv2.imshow(WINDOW, canvas.img)
            key = cv2.waitKey(frame_ms) & 0xFF
            if key == ord('q') or key == 27:
                break

            self._engine.wait(frame_ms)

        cv2.destroyAllWindows()

    def _make_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.zeros((self._board_h, self._total_w, 3), dtype=np.uint8)
        canvas.img[:] = (30, 30, 30)
        return canvas

    def _make_board_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.zeros((self._board_h, self._board_w, 3), dtype=np.uint8)
        return canvas

    def _on_mouse(self, event, x, y, flags, param):
        if not self._started:
            if event == cv2.EVENT_LBUTTONDOWN:
                self._started = True
            return
        if x >= self._board_w:
            return
        if event == cv2.EVENT_LBUTTONDBLCLK:
            self._engine.jump(x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            self._engine.click(x, y)
