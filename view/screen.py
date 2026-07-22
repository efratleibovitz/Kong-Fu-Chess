import cv2
import numpy as np

from view.img import Img
from view.constants import CELL, HUD_W, FPS,WINDOW,SHORT_REST_MS,LONG_REST_MS,BG_COLOR,CHANNELS_RGB
from engine.game_engine import GameEngine
from model.game_state import GameState
from view.loaders.sprite_loader import SpriteLoader
from view.renderers.board_renderer import BoardRenderer
from view.renderers.hud_renderer import HUDRenderer
from view.renderers.overlay_renderer import OverlayRenderer



class Screen:
    def __init__(self, engine: GameEngine, state: GameState, window_title: str | None = None):
        self._engine = engine
        self._state = state
        self._window_title = window_title
        loader = SpriteLoader()
        self._board_renderer = BoardRenderer(loader)
        self._hud_renderer = HUDRenderer(loader, state.board.num_rows * CELL)
        self._board_w = state.board.num_cols * CELL
        self._board_h = state.board.num_rows * CELL
        self._total_w = self._board_w + HUD_W
        self._overlay = OverlayRenderer(self._board_w, self._board_h)
        self._started = False
        self._needs_redraw = True
        self._rs = None

        state.events.subscribe('piece_settled', self._on_state_changed)
        state.events.subscribe('game_over', self._on_state_changed)
        state.events.subscribe('selection_changed', self._on_state_changed)
        state.events.subscribe('restarted', self._on_restart)

    def _on_state_changed(self, **_):
        self._needs_redraw = True

    def _on_restart(self, **_):
        self._started = False
        self._needs_redraw = True

    def run(self):
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        if self._window_title:
            cv2.setWindowTitle(WINDOW, self._window_title)
        cv2.resizeWindow(WINDOW, self._total_w, self._board_h)
        cv2.setMouseCallback(WINDOW, self._on_mouse)
        frame_ms = int(1000 / FPS)

        while True:
            self._engine.wait(frame_ms)

            if self._needs_redraw:
                self._rs = self._state.to_render_state()
                self._needs_redraw = False
            elif self._rs is not None:
                self._rs.clock_ms = self._state.clock
                self._update_cooldown_fills()

            canvas = self._make_canvas()
            board_canvas = self._make_board_canvas()

            if not self._started:
                self._overlay.draw_start(board_canvas)
            elif self._rs is not None:
                self._board_renderer.render(board_canvas, self._rs)
                if self._rs.game_over:
                    win_canvas = self._make_board_canvas()
                    self._overlay.draw_win(win_canvas, self._rs)
                    win_canvas.draw_on(board_canvas, 0, 0)

            board_canvas.draw_on(canvas, 0, 0)
            if self._rs is not None and self._started:
                hud = self._hud_renderer.make_panel(self._rs)
                hud.draw_on(canvas, self._board_w, 0)
            cv2.imshow(WINDOW, canvas.img)

            key = cv2.waitKey(frame_ms) & 0xFF
            if key == ord('q') or key == 27:
                break
            if key == ord('r'):
                self._engine.restart()
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()

    def _update_cooldown_fills(self):
        clock = self._state.clock
        for piece in self._rs.pieces:
            key = (piece.col, piece.row)
            expire = self._state.cooldowns.get(key, 0)
            if expire > clock:
                rest = self._state.rest_type.get(key, 'long_rest')
                total_ms = LONG_REST_MS if rest == 'long_rest' else SHORT_REST_MS
                piece.cooldown_fill = max(0.0, min(1.0, (expire - clock) / total_ms))
                piece.cooldown_is_long = rest == 'long_rest'
            else:
                piece.cooldown_fill = 0.0

    def _make_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.zeros((self._board_h, self._total_w, CHANNELS_RGB), dtype=np.uint8)
        canvas.img[:] = BG_COLOR
        return canvas

    def _make_board_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.zeros((self._board_h, self._board_w, CHANNELS_RGB), dtype=np.uint8)
        return canvas

    def _on_mouse(self, event, x, y, flags, param):
        if not self._started:
            if event == cv2.EVENT_LBUTTONDOWN:
                self._started = True
                self._needs_redraw = True
            return
        # Win32 HighGUI already maps mouse coords back into the original
        # image space on resize, so x/y need no manual rescaling here.
        if x >= self._board_w:
            return
        if event == cv2.EVENT_LBUTTONDBLCLK:
            self._engine.jump(x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            self._engine.click(x, y)
