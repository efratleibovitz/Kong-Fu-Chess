import cv2
import numpy as np

from view.img import Img
from view.constants import CELL, HUD_W, GOLD, HUD_BG, TEXT_COLOR,CAPTURED_SIZE
from view.render_state import RenderState
from view.loaders.sprite_loader import SpriteLoader
from view.renderers.history_renderer import HistoryRenderer


class HUDRenderer:
    def __init__(self, loader: SpriteLoader, board_h: int):
        self._loader = loader
        self._h = board_h
        self._captured_cache: dict[str, Img] = {}

    def make_panel(self, rs: RenderState) -> Img:
        panel = Img()
        panel.img = np.full((self._h, HUD_W, 3), HUD_BG, dtype=np.uint8)

        self._draw_player_section(panel, rs.white, 'w', y_start=self._h // 2 + 20)
        self._draw_player_section(panel, rs.black, 'b', y_start=20)

        total_sec = rs.clock_ms // 1000
        mins, secs = divmod(total_sec, 60)
        mid_y = self._h // 2
        cv2.line(panel.img, (10, mid_y), (HUD_W - 10, mid_y), (60, 60, 60), 1)
        panel.put_text(f"{mins:02}:{secs:02}", HUD_W // 2 - 30, mid_y - 8, 0.7, GOLD + (255,), 2)

        return panel

    def _draw_player_section(self, panel: Img, player, color: str, y_start: int):
        label_color = GOLD if color == 'w' else (200, 200, 200, 255)
        panel.put_text(player.name, 10, y_start + 20, 0.6, label_color, 2)
        panel.put_text(f"score: {player.score}", 10, y_start + 42, 0.55, TEXT_COLOR + (255,), 1)

        CAPTURED_ROWS = 2
        captured_area_h = CAPTURED_ROWS * (CAPTURED_SIZE + 2)
        x, y = 10, y_start + 65
        cap_bottom = y_start + 65 + captured_area_h
        for token in player.captured:
            sprite = self._get_captured_sprite(token)
            if sprite and y + CAPTURED_SIZE <= cap_bottom:
                if x + CAPTURED_SIZE > HUD_W:
                    x = 10
                    y += CAPTURED_SIZE + 2
                if y + CAPTURED_SIZE <= cap_bottom:
                    sprite.draw_on(panel, x, y)
                x += CAPTURED_SIZE + 2

        history_y = y_start + 65 + captured_area_h + 8
        max_h = (self._h // 2) - (65 + captured_area_h + 8) - 10
        HistoryRenderer.draw(panel, player.move_history, history_y, max_h, color)

    def _get_captured_sprite(self, token: str) -> Img | None:
        if token not in self._captured_cache:
            from view.constants import PieceState
            frames = self._loader.get(token, PieceState.IDLE)
            if not frames:
                return None
            import copy
            sprite = copy.copy(frames[0])
            sprite.img = cv2.resize(frames[0].img, (CAPTURED_SIZE, CAPTURED_SIZE))
            self._captured_cache[token] = sprite
        return self._captured_cache[token]
