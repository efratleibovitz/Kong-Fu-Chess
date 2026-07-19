import cv2
import numpy as np

from view.img import Img
from view.constants import (
    HUD_W, GOLD,
    ROW_BG_A, ROW_BG_B, LATEST_BG,
    HEADER_COLOR, INDEX_COLOR, TIME_COLOR,
    HISTORY_WHITE, HISTORY_BLACK, DIVIDER_DIM,
)

ROW_H = 18
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.42
LATEST_COLOR = GOLD
HISTORY_COLOR = {'w': HISTORY_WHITE, 'b': HISTORY_BLACK}


class HistoryRenderer:

    @staticmethod
    def draw(panel: Img, move_history: list, y_start: int, max_h: int, color: str):
        """move_history: list of (time_ms: int, notation: str) tuples."""
        if not move_history:
            return

        cv2.line(panel.img, (8, y_start - 4), (HUD_W - 8, y_start - 4), DIVIDER_DIM, 1)
        cv2.putText(panel.img, "Moves", (10, y_start + 8),
                    FONT, 0.38, HEADER_COLOR, 1, cv2.LINE_AA)

        max_rows = (max_h - 14) // ROW_H
        visible = move_history[-max_rows:]
        start_idx = len(move_history) - len(visible)

        text_color = HISTORY_COLOR[color]
        y = y_start + 16

        for i, (time_ms, notation) in enumerate(visible):
            global_idx = start_idx + i
            is_latest = (global_idx == len(move_history) - 1)

            bg = LATEST_BG if is_latest else (ROW_BG_A if i % 2 == 0 else ROW_BG_B)
            cv2.rectangle(panel.img, (8, y), (HUD_W - 8, y + ROW_H - 2), bg, -1)

            cv2.putText(panel.img, f"{global_idx + 1}.", (11, y + ROW_H - 5),
                        FONT, FONT_SCALE, INDEX_COLOR, 1, cv2.LINE_AA)

            total_sec = time_ms // 1000
            mins, secs = divmod(total_sec, 60)
            cv2.putText(panel.img, f"{mins:02}:{secs:02}", (32, y + ROW_H - 5),
                        FONT, FONT_SCALE, TIME_COLOR, 1, cv2.LINE_AA)

            color_used = tuple(LATEST_COLOR) if is_latest else text_color
            cv2.putText(panel.img, notation, (88, y + ROW_H - 5),
                        FONT, FONT_SCALE, color_used, 1, cv2.LINE_AA)

            y += ROW_H
