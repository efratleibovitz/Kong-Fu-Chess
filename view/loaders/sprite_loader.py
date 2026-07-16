import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "CTD26" / "py"))
from img import Img

ASSETS = pathlib.Path(__file__).parent.parent / "assets"
CELL = 100

# token prefix -> folder name  e.g. 'wK' -> 'KW', 'bP' -> 'PB'
# _KIND_MAP = {'K': 'K', 'Q': 'Q', 'R': 'R', 'B': 'B', 'N': 'N', 'P': 'P'}
# _COLOR_MAP = {'w': 'W', 'b': 'B'}

STATES = ('idle', 'move', 'jump', 'short_rest', 'long_rest')


def _folder(token: str, piece_set: str = 'pieces_mine') -> pathlib.Path:
    return ASSETS / piece_set / token


def _load_sprites(folder: pathlib.Path, state: str) -> list[Img]:
    sprites_dir = folder / 'states' / state / 'sprites'
    if not sprites_dir.exists():
        return []
    files = sorted(sprites_dir.glob('*.png'), key=lambda p: int(p.stem))
    return [Img().read(str(f), size=(CELL, CELL)) for f in files]


class SpriteLoader:
    def __init__(self, piece_set: str = 'pieces_mine'):
        self._cache: dict[str, dict[str, list[Img]]] = {}
        self._piece_set = piece_set

    def get(self, token: str, state: str = 'idle') -> list[Img]:
        if token not in self._cache:
            folder = _folder(token, self._piece_set)
            self._cache[token] = {s: _load_sprites(folder, s) for s in STATES}
        frames = self._cache[token].get(state, [])
        return frames if frames else self._cache[token].get('idle', [])
