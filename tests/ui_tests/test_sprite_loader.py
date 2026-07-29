"""
test_sprite_loader.py
Covers: view/loaders/sprite_loader.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import patch, MagicMock
from view.loaders.sprite_loader import SpriteLoader, _folder
from view.constants import PieceState


def _fake_img():
    img = MagicMock()
    img.img = None
    return img


def _make_loader_with_cache(token, states_frames: dict) -> SpriteLoader:
    loader = SpriteLoader.__new__(SpriteLoader)
    loader._piece_set = 'pieces_mine'
    loader._cache = {token: states_frames}
    return loader


def _full_cache(idle_frames):
    return {s: (idle_frames if s == PieceState.IDLE else []) for s in PieceState}


# ── _folder mapping ───────────────────────────────────────────────────────────

def test_folder_white_king():
    assert _folder('wK').name == 'wK'

def test_folder_black_pawn():
    assert _folder('bP').name == 'bP'

def test_folder_white_knight():
    assert _folder('wN').name == 'wN'


# ── cache hit ─────────────────────────────────────────────────────────────────

def test_get_returns_cached_frames():
    fake = [_fake_img()]
    loader = _make_loader_with_cache('wP', _full_cache(fake))
    assert loader.get('wP', PieceState.IDLE) is fake

def test_get_called_twice_uses_cache():
    fake = [_fake_img()]
    loader = _make_loader_with_cache('wP', _full_cache(fake))
    loader.get('wP', PieceState.IDLE)
    assert loader.get('wP', PieceState.IDLE) is fake


# ── fallback to idle ──────────────────────────────────────────────────────────

def test_get_falls_back_to_idle_when_state_empty():
    idle_frames = [_fake_img()]
    loader = _make_loader_with_cache('wR', _full_cache(idle_frames))
    assert loader.get('wR', PieceState.MOVE) is idle_frames

def test_get_returns_empty_when_idle_also_missing():
    loader = _make_loader_with_cache('wR', {s: [] for s in PieceState})
    assert loader.get('wR', PieceState.MOVE) == []


# ── no-asset path (folder missing) ───────────────────────────────────────────

def test_get_returns_empty_when_folder_missing():
    loader = SpriteLoader()
    with patch('view.loaders.sprite_loader._load_sprites', return_value=[]):
        assert loader.get('wQ', PieceState.IDLE) == []
