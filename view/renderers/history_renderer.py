import cv2
import numpy as np

from view.img import Img
from view.constants import HUD_W, GOLD, TEXT_COLOR
from model.game_state import GameState

ROW_H = 18
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.42
ROW_BG_A = (35, 35, 35)
ROW_BG_B = (28, 28, 28)
LATEST_BG = (50, 40, 20)
HISTORY_COLOR = {'w': (210, 210, 210), 'b': (150, 195, 255)}
LATEST_COLOR = GOLD
HEADER_COLOR = (120, 120, 120)


class HistoryRenderer:

    @staticmethod
    def draw(panel: Img, state: GameState, y_start: int, max_h: int, color: str):
        moves = [m for m in state.move_history if m.color == color]
        if not moves:
            return

        # section header
        cv2.line(panel.img, (8, y_start - 4), (HUD_W - 8, y_start - 4), (55, 55, 55), 1)
        cv2.putText(panel.img, "Moves", (10, y_start + 8),
                    FONT, 0.38, HEADER_COLOR, 1, cv2.LINE_AA)

        max_rows = (max_h - 14) // ROW_H
        visible = moves[-max_rows:]
        start_idx = len(moves) - len(visible)  # move number offset

        text_color = HISTORY_COLOR[color]
        y = y_start + 16

        for i, record in enumerate(visible):
            global_idx = start_idx + i
            is_latest = (global_idx == len(moves) - 1)

            # row background
            bg = LATEST_BG if is_latest else (ROW_BG_A if i % 2 == 0 else ROW_BG_B)
            cv2.rectangle(panel.img, (8, y), (HUD_W - 8, y + ROW_H - 2), bg, -1)

            # move number
            move_num = f"{global_idx + 1}."
            cv2.putText(panel.img, move_num, (11, y + ROW_H - 5),
                        FONT, FONT_SCALE, (100, 100, 100), 1, cv2.LINE_AA)

            # time
            total_sec = record.time_ms // 1000
            mins, secs = divmod(total_sec, 60)
            time_str = f"{mins:02}:{secs:02}"
            cv2.putText(panel.img, time_str, (32, y + ROW_H - 5),
                        FONT, FONT_SCALE, (90, 90, 90), 1, cv2.LINE_AA)

            # notation
            color_used = tuple(LATEST_COLOR) if is_latest else text_color
            cv2.putText(panel.img, record.notation, (88, y + ROW_H - 5),
                        FONT, FONT_SCALE, color_used, 1, cv2.LINE_AA)

            y += ROW_H
