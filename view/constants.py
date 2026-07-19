import pathlib
from enum import Enum

CELL = 100
HUD_W = 220
FPS = 30

BOARD_IMG = pathlib.Path(__file__).parent / "assets" / "board.png"
ASSETS = pathlib.Path(__file__).parent.parent / "assets"

# colors (BGR)
GOLD = (0, 215, 255)
WHITE = (255, 255, 255)
RED = (0, 0, 255)
SILVER = (200, 200, 200)
HUD_BG = (20, 20, 20)
TEXT_COLOR = (220, 220, 220)
DIVIDER = (60, 60, 60)
DIVIDER_DIM = (55, 55, 55)
HIGHLIGHT_SELECTED = GOLD
HIGHLIGHT_PENDING = (0, 120, 255)
COOLDOWN_LONG = (0, 120, 255)
COOLDOWN_SHORT = (255, 160, 0)
COOLDOWN_BG = (50, 50, 50)
ROW_BG_A = (35, 35, 35)
ROW_BG_B = (28, 28, 28)
LATEST_BG = (50, 40, 20)
HEADER_COLOR = (120, 120, 120)
INDEX_COLOR = (100, 100, 100)
TIME_COLOR = (90, 90, 90)
HISTORY_WHITE = (210, 210, 210)
HISTORY_BLACK = (150, 195, 255)
WINDOW = "Kong-Fu Chess"
LONG_REST_MS = 2000
SHORT_REST_MS = 1000
BG_COLOR = (30, 30, 30)
CHANNELS_RGB = 3
CHANNELS_RGBA = 4
CAPTURED_SIZE = 28
class PieceState(Enum):
    IDLE = 'idle'
    MOVE = 'move'
    JUMP = 'jump'
    SHORT_REST = 'short_rest'
    LONG_REST = 'long_rest'
