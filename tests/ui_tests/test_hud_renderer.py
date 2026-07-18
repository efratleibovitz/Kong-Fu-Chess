"""
test_hud_renderer.py
Covers: view/renderers/hud_renderer.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from unittest.mock import MagicMock, patch
from view.renderers.hud_renderer import HUDRenderer, HUD_W
from view.render_state import RenderState, PlayerRenderInfo


def _player(name='White', score=0, captured=None):
    return PlayerRenderInfo(name=name, score=score, captured=captured or [], move_history=[])


def _make_rs(clock_ms=0, white=None, black=None):
    return RenderState(
        num_cols=8, num_rows=8,
        pieces=[], selected_col=None, selected_row=None,
        pending_destinations=[],
        clock_ms=clock_ms,
        white=white or _player('White'),
        black=black or _player('Black'),
        game_over=False, loser=None,
    )


def _make_renderer():
    loader = MagicMock()
    loader.get.return_value = []
    renderer = HUDRenderer.__new__(HUDRenderer)
    renderer._loader = loader
    renderer._h = 800
    renderer._captured_cache = {}
    return renderer, loader


# ── panel dimensions ──────────────────────────────────────────────────────────

def test_panel_width_is_hud_w():
    renderer, _ = _make_renderer()
    panel = renderer.make_panel(_make_rs())
    assert panel.img.shape[1] == HUD_W

def test_panel_height_matches_board():
    renderer, _ = _make_renderer()
    panel = renderer.make_panel(_make_rs())
    assert panel.img.shape[0] == renderer._h


# ── clock formatting ──────────────────────────────────────────────────────────

def test_clock_zero_no_crash():
    renderer, _ = _make_renderer()
    assert renderer.make_panel(_make_rs(clock_ms=0)) is not None

def test_clock_one_minute_no_crash():
    renderer, _ = _make_renderer()
    assert renderer.make_panel(_make_rs(clock_ms=61000)) is not None


# ── player info ───────────────────────────────────────────────────────────────

def test_panel_renders_with_custom_names():
    renderer, _ = _make_renderer()
    rs = _make_rs(white=_player('Alice'), black=_player('Bob'))
    assert renderer.make_panel(rs) is not None

def test_panel_renders_with_score():
    renderer, _ = _make_renderer()
    rs = _make_rs(white=_player(score=9))
    assert renderer.make_panel(rs) is not None


# ── captured pieces ───────────────────────────────────────────────────────────

def test_captured_piece_triggers_loader_get():
    renderer, loader = _make_renderer()
    fake_img = MagicMock()
    fake_img.img = np.zeros((28, 28, 3), dtype=np.uint8)
    loader.get.return_value = [fake_img]
    rs = _make_rs(white=_player(captured=['bP']))
    renderer.make_panel(rs)
    from view.constants import PieceState
    loader.get.assert_called_with('bP', PieceState.IDLE)

def test_captured_sprite_is_cached():
    renderer, loader = _make_renderer()
    fake_img = MagicMock()
    fake_img.img = np.zeros((100, 100, 3), dtype=np.uint8)
    loader.get.return_value = [fake_img]
    rs = _make_rs(white=_player(captured=['bP', 'bP']))
    renderer.make_panel(rs)
    bP_calls = [c for c in loader.get.call_args_list if c[0][0] == 'bP']
    assert len(bP_calls) == 1

def test_no_loader_call_when_no_captures():
    renderer, loader = _make_renderer()
    renderer.make_panel(_make_rs())
    loader.get.assert_not_called()
