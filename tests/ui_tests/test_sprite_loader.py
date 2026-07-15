"""
test_sprite_loader.py
Covers: view/loaders/sprite_loader.py

Tests that SpriteLoader:
- returns cached results on repeated calls (no double-loading)
- falls back to 'idle' when requested state has no frames
- returns empty list when token folder doesn't exist
- correctly maps token to folder name (color + kind)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import patch, MagicMock
from view.loaders.sprite_loader import SpriteLoader, _folder


def _fake_img():
    img = MagicMock()
    img.img = None
    return img


def _make_loader_with_cache(token, states_frames: dict) -> SpriteLoader:
    """Returns a SpriteLoader with pre-populated cache for token."""
    loader = SpriteLoader.__new__(SpriteLoader)
    loader._piece_set = 'pieces1'
    loader._cache = {token: states_frames}
    return loader


# ── _folder mapping ──────────────────────────────────────────────────────────

def test_folder_white_king():
    p = _folder('wK')
    assert p.name == 'KW'

def test_folder_black_pawn():
    p = _folder('bP')
    assert p.name == 'PB'

def test_folder_white_knight():
    p = _folder('wN')
    assert p.name == 'NW'


# ── cache hit ────────────────────────────────────────────────────────────────

def test_get_returns_cached_frames():
    fake = [_fake_img()]
    loader = _make_loader_with_cache('wP', {'idle': fake, 'move': [], 'jump': [], 'short_rest': [], 'long_rest': []})
    result = loader.get('wP', 'idle')
    assert result is fake

def test_get_called_twice_uses_cache():
    fake = [_fake_img()]
    loader = _make_loader_with_cache('wP', {'idle': fake, 'move': [], 'jump': [], 'short_rest': [], 'long_rest': []})
    loader.get('wP', 'idle')
    result = loader.get('wP', 'idle')
    assert result is fake


# ── fallback to idle ─────────────────────────────────────────────────────────

def test_get_falls_back_to_idle_when_state_empty():
    idle_frames = [_fake_img()]
    loader = _make_loader_with_cache('wR', {
        'idle': idle_frames, 'move': [], 'jump': [], 'short_rest': [], 'long_rest': []
    })
    result = loader.get('wR', 'move')
    assert result is idle_frames

def test_get_returns_empty_when_idle_also_missing():
    loader = _make_loader_with_cache('wR', {
        'idle': [], 'move': [], 'jump': [], 'short_rest': [], 'long_rest': []
    })
    result = loader.get('wR', 'move')
    assert result == []


# ── no-asset path (folder missing) ───────────────────────────────────────────

def test_get_returns_empty_when_folder_missing():
    loader = SpriteLoader()
    # patch _load_sprites to return [] for all states
    with patch('view.loaders.sprite_loader._load_sprites', return_value=[]):
        result = loader.get('wQ', 'idle')
    assert result == []
