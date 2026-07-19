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
HUD_BG = (20, 20, 20)
TEXT_COLOR = (220, 220, 220)
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
