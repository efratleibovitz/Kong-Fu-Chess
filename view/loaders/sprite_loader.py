import pathlib

from view.img import Img
from view.constants import CELL, PieceState,ASSETS


def _folder(token: str, piece_set: str = 'pieces_mine') -> pathlib.Path:
    return ASSETS / piece_set / token


def _load_sprites(folder: pathlib.Path, state: PieceState) -> list[Img]:
    sprites_dir = folder / 'states' / state.value / 'sprites'
    if not sprites_dir.exists():
        return []
    files = sorted(sprites_dir.glob('*.png'), key=lambda p: int(p.stem))
    return [Img().read(str(f), size=(CELL, CELL)) for f in files]


class SpriteLoader:
    def __init__(self, piece_set: str = 'pieces_mine'):
        self._cache: dict[str, dict[PieceState, list[Img]]] = {}
        self._piece_set = piece_set

    def get(self, token: str, state: PieceState = PieceState.IDLE) -> list[Img]:
        if token not in self._cache:
            folder = _folder(token, self._piece_set)
            self._cache[token] = {s: _load_sprites(folder, s) for s in PieceState}
        frames = self._cache[token].get(state, [])
        return frames if frames else self._cache[token].get(PieceState.IDLE, [])
