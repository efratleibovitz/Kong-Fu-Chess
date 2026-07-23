import cv2
import numpy as np

from view.img import Img
from view.constants import GOLD, WHITE, RED, BOARD_IMG
from view.render_state import RenderState


class OverlayRenderer:
    def __init__(self, w: int, h: int):
        self._w = w
        self._h = h
        self._bg = Img().read(str(BOARD_IMG), size=(w, h))

    def draw_start(self, canvas: Img):
        self._draw_dimmed_bg(canvas)
        cx, cy = self._w // 2, self._h // 2
        canvas.put_text("KONG-FU CHESS", cx - 200, cy - 60, 1.8, GOLD + (255,), 3)
        canvas.put_text("Click to start", cx - 100, cy + 20, 1.0, WHITE + (255,), 2)

    def draw_win(self, canvas: Img, rs: RenderState):
        self._draw_dimmed_bg(canvas)
        cx, cy = self._w // 2, self._h // 2
        canvas.put_text("GAME OVER", cx - 160, cy - 60, 2.0, RED + (255,), 4)
        if rs.loser is not None:
            winner = 'w' if rs.loser == 'b' else 'b'
            winner_info = rs.white if winner == 'w' else rs.black
            canvas.put_text(f"{winner_info.name} wins!", cx - 120, cy + 10, 1.4, GOLD + (255,), 3)
            canvas.put_text(f"Score: {winner_info.score}", cx - 70, cy + 60, 1.0, WHITE + (255,), 2)
        canvas.put_text("Press Q to quit  |  R to restart", cx - 210, cy + 110, 0.8, WHITE + (255,), 1)

    def draw_main_menu(self, canvas: Img, play_rect, room_rect, hover=None, error: str | None = None):
        self._draw_dimmed_bg(canvas)
        cx = self._w // 2
        canvas.put_text("KONG-FU CHESS", cx - 200, 100, 1.8, GOLD + (255,), 3)
        if error:
            canvas.put_text(error, cx - min(len(error) * 5, cx - 20), 220, 0.7, RED + (255,), 2)
        self._draw_button(canvas, play_rect, "PLAY", hover == "play")
        self._draw_button(canvas, room_rect, "ROOM", hover == "room")

    def draw_room_menu(self, canvas: Img, room_code, code_rect, create_rect, join_rect, back_rect, cursor_visible):
        self._draw_dimmed_bg(canvas)
        cx = self._w // 2
        canvas.put_text("Enter Room Code", cx - 150, 100, 1.2, WHITE + (255,), 2)

        x1, y1, x2, y2 = code_rect
        canvas.draw_rect(x1, y1, x2, y2, WHITE + (255,), 2)
        displayed = room_code + ("|" if cursor_visible else "")
        canvas.put_text(displayed, x1 + 10, y2 - 15, 0.9, WHITE + (255,), 2)

        self._draw_button(canvas, create_rect, "CREATE", False)
        self._draw_button(canvas, join_rect, "JOIN", False)
        self._draw_button(canvas, back_rect, "BACK", False)

    def _draw_button(self, canvas: Img, rect, label: str, hovered: bool):
        x1, y1, x2, y2 = rect
        color = GOLD if hovered else WHITE
        canvas.draw_rect(x1, y1, x2, y2, color + (255,), 3 if hovered else 2)
        text_x = x1 + (x2 - x1) // 2 - len(label) * 10
        text_y = y1 + (y2 - y1) // 2 + 10
        canvas.put_text(label, text_x, text_y, 1.0, color + (255,), 2)

    def _draw_dimmed_bg(self, canvas: Img):
        self._bg.draw_on(canvas, 0, 0)
        dim = np.zeros((self._h, self._w, 3), dtype=np.uint8)
        cv2.addWeighted(dim, 0.6, canvas.img, 0.4, 0, canvas.img)
