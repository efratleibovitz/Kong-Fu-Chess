"""view/menu_screen.py

Graphical pre-game menu: PLAY vs ROOM, and the ROOM sub-screen's room-code
entry plus Create/Join/Back. Runs before any GameEngine/GameState exists,
so it needs neither - just view.constants sizing. Opens the same WINDOW
Screen uses right after, so there's no flicker between menu and game.
"""

import cv2
import numpy as np

from view.img import Img
from view.constants import CELL, HUD_W, FPS, WINDOW, BG_COLOR, CHANNELS_RGB
from view.renderers.overlay_renderer import OverlayRenderer

MAX_ROOM_CODE_LEN = 40


class MenuScreen:
    def __init__(self):
        self._board_w = CELL * 8
        self._board_h = CELL * 8
        self._total_w = self._board_w + HUD_W
        self._overlay = OverlayRenderer(self._board_w, self._board_h)
        self._screen = "main"
        self._room_code = ""
        self._hover = None
        self._frame = 0
        self._result = None

    def run(self) -> tuple:
        """Returns ("quick_match", None) | ("create", None) |
        ("join", room_code) | ("quit", None)."""
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, self._total_w, self._board_h)
        cv2.setMouseCallback(WINDOW, self._on_mouse)
        frame_ms = int(1000 / FPS)

        while self._result is None:
            canvas = self._make_canvas()
            board_canvas = self._make_board_canvas()
            self._render(board_canvas)
            board_canvas.draw_on(canvas, 0, 0)
            cv2.imshow(WINDOW, canvas.img)

            key = cv2.waitKey(frame_ms) & 0xFF
            if key == 27:
                return ("quit", None)
            if self._screen == "room":
                self._handle_key(key)
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                return ("quit", None)
            self._frame += 1

        return self._result

    def _render(self, board_canvas: Img):
        if self._screen == "main":
            self._overlay.draw_main_menu(board_canvas, self._play_rect(), self._room_rect(), self._hover)
        else:
            cursor_visible = (self._frame // (FPS // 2 or 1)) % 2 == 0
            self._overlay.draw_room_menu(
                board_canvas, self._room_code, self._code_rect(),
                self._create_rect(), self._join_rect(), self._back_rect(),
                cursor_visible,
            )

    def _make_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.zeros((self._board_h, self._total_w, CHANNELS_RGB), dtype=np.uint8)
        canvas.img[:] = BG_COLOR
        return canvas

    def _make_board_canvas(self) -> Img:
        canvas = Img()
        canvas.img = np.zeros((self._board_h, self._board_w, CHANNELS_RGB), dtype=np.uint8)
        return canvas

    # --- button/box geometry (board-relative) ---

    def _play_rect(self):
        cx = self._board_w // 2
        return (cx - 150, 300, cx + 150, 370)

    def _room_rect(self):
        cx = self._board_w // 2
        return (cx - 150, 400, cx + 150, 470)

    def _code_rect(self):
        cx = self._board_w // 2
        return (cx - 200, 300, cx + 200, 350)

    def _create_rect(self):
        cx = self._board_w // 2
        return (cx - 200, 400, cx - 20, 460)

    def _join_rect(self):
        cx = self._board_w // 2
        return (cx + 20, 400, cx + 200, 460)

    def _back_rect(self):
        cx = self._board_w // 2
        return (cx - 100, 480, cx + 100, 530)

    @staticmethod
    def _point_in(x: int, y: int, rect) -> bool:
        x1, y1, x2, y2 = rect
        return x1 <= x <= x2 and y1 <= y <= y2

    # --- input handlers ---

    def _handle_key(self, key: int):
        if key in (8, 127):  # Backspace
            self._room_code = self._room_code[:-1]
        elif key == 13:  # Enter
            if self._room_code:
                self._result = ("join", self._room_code)
        elif 32 <= key <= 126 and len(self._room_code) < MAX_ROOM_CODE_LEN:
            self._room_code += chr(key)

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self._update_hover(x, y)
            return
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if self._screen == "main":
            self._handle_main_click(x, y)
        else:
            self._handle_room_click(x, y)

    def _update_hover(self, x: int, y: int):
        if self._screen != "main":
            self._hover = None
            return
        if self._point_in(x, y, self._play_rect()):
            self._hover = "play"
        elif self._point_in(x, y, self._room_rect()):
            self._hover = "room"
        else:
            self._hover = None

    def _handle_main_click(self, x: int, y: int):
        if self._point_in(x, y, self._play_rect()):
            self._result = ("quick_match", None)
        elif self._point_in(x, y, self._room_rect()):
            self._screen = "room"

    def _handle_room_click(self, x: int, y: int):
        if self._point_in(x, y, self._create_rect()):
            self._result = ("create", self._room_code or None)
        elif self._point_in(x, y, self._join_rect()) and self._room_code:
            self._result = ("join", self._room_code)
        elif self._point_in(x, y, self._back_rect()):
            self._screen = "main"
            self._room_code = ""
