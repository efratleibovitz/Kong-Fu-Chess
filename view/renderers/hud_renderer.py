import pathlib
import sys

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "CTD26" / "py"))
from img import Img

from model.game_state import GameState
from view.loaders.sprite_loader import SpriteLoader, CELL

HUD_W = 220
HUD_BG = (20, 20, 20)
TEXT_COLOR = (220, 220, 220)
GOLD = (0, 215, 255)
CAPTURED_SIZE = 28


class HUDRenderer:
    def __init__(self, loader: SpriteLoader, board_h: int):
        self._loader = loader
        self._h = board_h
        self._captured_cache: dict[str, Img] = {}

    def make_panel(self, state: GameState) -> Img:
        panel = Img()
        panel.img = np.full((self._h, HUD_W, 3), HUD_BG, dtype=np.uint8)

        # --- White player (bottom) ---
        self._draw_player_section(panel, state, 'w', y_start=self._h // 2 + 20)

        # --- Black player (top) ---
        self._draw_player_section(panel, state, 'b', y_start=20)

        # --- Clock (center) ---
        total_sec = state.clock // 1000
        mins, secs = divmod(total_sec, 60)
        clock_str = f"{mins:02}:{secs:02}"
        mid_y = self._h // 2
        cv2.line(panel.img, (10, mid_y), (HUD_W - 10, mid_y), (60, 60, 60), 1)
        panel.put_text(clock_str, HUD_W // 2 - 30, mid_y - 8, 0.7, GOLD + (255,), 2)

        return panel

    def _draw_player_section(self, panel: Img, state: GameState, color: str, y_start: int):
        name = state.player_names[color]
        score = state.scores[color]
        label_color = GOLD if color == 'w' else (200, 200, 200, 255)
        panel.put_text(f"{name}", 10, y_start + 20, 0.6, label_color, 2)
        panel.put_text(f"score: {score}", 10, y_start + 42, 0.55, TEXT_COLOR + (255,), 1)

        captured = state.captured[color]
        x, y = 10, y_start + 65
        for token in captured:
            sprite = self._get_captured_sprite(token)
            if sprite and x + CAPTURED_SIZE <= HUD_W:
                sprite.draw_on(panel, x, y)
                x += CAPTURED_SIZE + 2
                if x + CAPTURED_SIZE > HUD_W:
                    x = 10
                    y += CAPTURED_SIZE + 2

    def _get_captured_sprite(self, token: str) -> Img | None:
        if token not in self._captured_cache:
            frames = self._loader.get(token, 'idle')
            if not frames:
                return None
            import copy
            sprite = copy.copy(frames[0])
            sprite.img = cv2.resize(frames[0].img, (CAPTURED_SIZE, CAPTURED_SIZE))
            self._captured_cache[token] = sprite
        return self._captured_cache[token]
