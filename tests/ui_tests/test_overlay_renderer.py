"""
test_overlay_renderer.py
Covers: view/renderers/overlay_renderer.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from unittest.mock import MagicMock, patch
from view.renderers.overlay_renderer import OverlayRenderer
from view.render_state import RenderState, PlayerRenderInfo


def _player(name='White', score=0):
    return PlayerRenderInfo(name=name, score=score, captured=[], move_history=[])


def _make_rs(loser=None, white_score=5, black_score=3):
    return RenderState(
        num_cols=8, num_rows=8,
        pieces=[], selected_col=None, selected_row=None,
        pending_destinations=[],
        clock_ms=0,
        white=_player('White', white_score),
        black=_player('Black', black_score),
        game_over=loser is not None,
        loser=loser,
    )


def _make_renderer():
    with patch('view.renderers.overlay_renderer.Img') as MockImg:
        mock_bg = MagicMock()
        mock_bg.img = np.zeros((800, 800, 3), dtype=np.uint8)
        MockImg.return_value.read.return_value = mock_bg
        renderer = OverlayRenderer(800, 800)
        renderer._bg = mock_bg
    return renderer


def _make_canvas():
    canvas = MagicMock()
    canvas.img = np.zeros((800, 800, 3), dtype=np.uint8)
    canvas.put_text = MagicMock()
    return canvas


# ── draw_start ────────────────────────────────────────────────────────────────

def test_draw_start_calls_put_text_twice():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_start(canvas)
    assert canvas.put_text.call_count == 2

def test_draw_start_shows_title():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_start(canvas)
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('KONG' in t for t in texts)

def test_draw_start_shows_click_to_start():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_start(canvas)
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('Click' in t or 'start' in t.lower() for t in texts)


# ── draw_win ──────────────────────────────────────────────────────────────────

def test_draw_win_shows_game_over():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='b'))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('GAME' in t for t in texts)

def test_draw_win_white_wins_when_black_loses():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='b'))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('White' in t for t in texts)

def test_draw_win_black_wins_when_white_loses():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='w'))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('Black' in t for t in texts)

def test_draw_win_shows_score():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='b', white_score=7))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('7' in t for t in texts)

def test_draw_win_no_crash_when_loser_is_none():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser=None))


# ── _draw_dimmed_bg ───────────────────────────────────────────────────────────

def test_dimmed_bg_calls_add_weighted():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted') as mock_blend:
        renderer._draw_dimmed_bg(canvas)
        mock_blend.assert_called_once()
