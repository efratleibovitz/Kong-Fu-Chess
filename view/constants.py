import pathlib
from enum import Enum

CELL = 100
HUD_W = 220
FPS = 30

BOARD_IMG = pathlib.Path(__file__).parent / "assets" / "board.png"

# colors (BGR)
GOLD = (0, 215, 255)
WHITE = (255, 255, 255)
RED = (0, 0, 255)
HUD_BG = (20, 20, 20)
TEXT_COLOR = (220, 220, 220)
WINDOW = "Kong-Fu Chess"


class PieceState(Enum):
    IDLE = 'idle'
    MOVE = 'move'
    JUMP = 'jump'
    SHORT_REST = 'short_rest'
    LONG_REST = 'long_rest'
