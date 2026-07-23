"""
test_board_renderer.py
Covers: view/renderers/board_renderer.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from unittest.mock import MagicMock, patch
from view.renderers.board_renderer import BoardRenderer
from view.render_state import RenderState, PieceRenderInfo, MoveArrow, PlayerRenderInfo
from view.constants import PieceState


def _make_renderer():
    loader = MagicMock()
    loader.get.return_value = []
    with patch('view.renderers.board_renderer.Img') as MockImg:
        mock_board = MagicMock()
        mock_board.img = np.zeros((800, 800, 3), dtype=np.uint8)
        MockImg.return_value.read.return_value = mock_board
        renderer = BoardRenderer.__new__(BoardRenderer)
        renderer._loader = loader
        renderer._board_img = mock_board
        renderer._frame_counters = {}
        renderer._last_tick = 0.0
    return renderer, loader


def _make_canvas():
    canvas = MagicMock()
    canvas.img = np.zeros((800, 800, 3), dtype=np.uint8)
    return canvas


def _player():
    return PlayerRenderInfo(name='White', score=0, captured=[], move_history=[])


def _make_rs(pieces=None, selected_col=None, selected_row=None, destinations=None):
    return RenderState(
        num_cols=8, num_rows=8,
        pieces=pieces or [],
        selected_col=selected_col,
        selected_row=selected_row,
        pending_destinations=destinations or [],
        clock_ms=0,
        white=_player(), black=_player(),
        game_over=False, loser=None,
    )


# ── _advance_frame ────────────────────────────────────────────────────────────

def test_advance_frame_stays_in_bounds():
    renderer, _ = _make_renderer()
    idx = renderer._advance_frame('key1', 4, 0.5, PieceState.MOVE)
    assert 0 <= idx < 4

def test_advance_frame_wraps_around():
    renderer, _ = _make_renderer()
    renderer._frame_counters['key1'] = 3.9
    idx = renderer._advance_frame('key1', 4, 1.0, PieceState.MOVE)
    assert 0 <= idx < 4


# ── _draw_cooldown_bar ────────────────────────────────────────────────────────

def test_draw_cooldown_bar_skips_when_fill_zero():
    renderer, _ = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.rectangle') as mock_rect:
        renderer._draw_cooldown_bar(canvas, 0, 0, 0.0, False)
        mock_rect.assert_not_called()

def test_draw_cooldown_bar_draws_when_fill_nonzero():
    renderer, _ = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.rectangle') as mock_rect:
        renderer._draw_cooldown_bar(canvas, 0, 0, 0.5, True)
        assert mock_rect.call_count == 2  # background + fill


# ── render calls loader ───────────────────────────────────────────────────────

def test_render_calls_loader_for_each_piece():
    renderer, loader = _make_renderer()
    pieces = [
        PieceRenderInfo('wP', 0, 0, PieceState.IDLE, 0.0, False),
        PieceRenderInfo('bR', 2, 0, PieceState.IDLE, 0.0, False),
    ]
    rs = _make_rs(pieces=pieces)
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0):
        renderer._last_tick = 1.0
        renderer.render(canvas, rs)
    tokens = [c[0][0] for c in loader.get.call_args_list]
    assert 'wP' in tokens
    assert 'bR' in tokens

def test_render_skips_when_no_pieces():
    renderer, loader = _make_renderer()
    rs = _make_rs(pieces=[])
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0):
        renderer._last_tick = 1.0
        renderer.render(canvas, rs)
    loader.get.assert_not_called()


# ── highlights ────────────────────────────────────────────────────────────────

def test_render_draws_highlight_for_selected():
    renderer, _ = _make_renderer()
    rs = _make_rs(selected_col=2, selected_row=3)
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0), \
         patch('cv2.rectangle'), \
         patch('cv2.addWeighted') as mock_blend:
        renderer._last_tick = 1.0
        renderer.render(canvas, rs)
        assert mock_blend.call_count >= 1

def test_render_draws_highlight_for_pending_destination():
    renderer, _ = _make_renderer()
    rs = _make_rs(destinations=[MoveArrow(4, 5)])
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0), \
         patch('cv2.rectangle'), \
         patch('cv2.addWeighted') as mock_blend:
        renderer._last_tick = 1.0
        renderer.render(canvas, rs)
        assert mock_blend.call_count >= 1


# ── click feedback message ────────────────────────────────────────────────────

def test_render_draws_message_when_set():
    renderer, _ = _make_renderer()
    rs = _make_rs()
    rs.message = "Not your piece"
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0):
        renderer._last_tick = 1.0
        renderer.render(canvas, rs)
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert "Not your piece" in texts

def test_render_skips_message_when_none():
    renderer, _ = _make_renderer()
    rs = _make_rs()
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0):
        renderer._last_tick = 1.0
        renderer.render(canvas, rs)
    canvas.put_text.assert_not_called()

def test_draw_message_centers_text_horizontally():
    renderer, _ = _make_renderer()
    canvas = _make_canvas()
    renderer._draw_message(canvas, "Not your piece")
    x = canvas.put_text.call_args[0][1]
    assert 0 < x < canvas.img.shape[1]
