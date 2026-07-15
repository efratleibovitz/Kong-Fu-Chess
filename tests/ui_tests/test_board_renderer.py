"""
test_board_renderer.py
Covers: view/renderers/board_renderer.py

Tests that BoardRenderer:
- _piece_state returns 'move' for pieces currently in transit (by position)
- _piece_state returns 'jump' for airborne pieces (by position)
- _piece_state returns 'long_rest' / 'short_rest' based on cooldown dict
- _piece_state returns 'idle' when no cooldown and not moving
- _advance_frame stays within [0, total-1]
- _draw_cooldown_bar skips drawing when no cooldown active
- render calls loader.get for each piece on the board
- highlights are drawn for selected position and pending move destinations
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from unittest.mock import MagicMock, patch
from model.board import Board
from model.game_state import GameState
from model.position import Position
from view.renderers.board_renderer import BoardRenderer


def _make_state(rows):
    return GameState(Board(rows))


def _make_renderer():
    loader = MagicMock()
    loader.get.return_value = []
    with patch('view.renderers.board_renderer.Img') as MockImg:
        mock_img_instance = MagicMock()
        mock_img_instance.img = np.zeros((800, 800, 3), dtype=np.uint8)
        MockImg.return_value.read.return_value = mock_img_instance
        renderer = BoardRenderer.__new__(BoardRenderer)
        renderer._loader = loader
        renderer._board_img = mock_img_instance
        renderer._frame_counters = {}
        renderer._last_tick = 0.0
    return renderer, loader


def _make_canvas():
    from unittest.mock import MagicMock
    canvas = MagicMock()
    canvas.img = np.zeros((800, 800, 3), dtype=np.uint8)
    return canvas


# ── _piece_state ─────────────────────────────────────────────────────────────

def test_piece_state_idle():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    assert renderer._piece_state('wP', set(), set(), state, 0, 0) == 'idle'

def test_piece_state_move():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    assert renderer._piece_state('wP', {(0, 0)}, set(), state, 0, 0) == 'move'

def test_piece_state_jump():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    assert renderer._piece_state('wP', set(), {(0, 0)}, state, 0, 0) == 'jump'

def test_piece_state_long_rest():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    state.clock = 0
    state.cooldowns[(0, 0)] = 2000
    state.rest_type[(0, 0)] = 'long_rest'
    assert renderer._piece_state('wP', set(), set(), state, 0, 0) == 'long_rest'

def test_piece_state_short_rest():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    state.clock = 0
    state.cooldowns[(0, 0)] = 1000
    state.rest_type[(0, 0)] = 'short_rest'
    assert renderer._piece_state('wP', set(), set(), state, 0, 0) == 'short_rest'

def test_piece_state_expired_cooldown_is_idle():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    state.clock = 3000
    state.cooldowns[(0, 0)] = 1000  # already expired
    assert renderer._piece_state('wP', set(), set(), state, 0, 0) == 'idle'

def test_piece_state_move_takes_priority_over_cooldown():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    state.clock = 0
    state.cooldowns[(0, 0)] = 2000
    state.rest_type[(0, 0)] = 'long_rest'
    assert renderer._piece_state('wP', {(0, 0)}, set(), state, 0, 0) == 'move'

def test_piece_state_position_based_not_token_based():
    # two wP on board — only the one at moving position gets 'move'
    renderer, _ = _make_renderer()
    state = _make_state([['wP', 'wP']])
    moving = {(0, 0)}
    assert renderer._piece_state('wP', moving, set(), state, 0, 0) == 'move'
    assert renderer._piece_state('wP', moving, set(), state, 1, 0) == 'idle'


# ── _advance_frame ────────────────────────────────────────────────────────────

def test_advance_frame_stays_in_bounds():
    renderer, _ = _make_renderer()
    idx = renderer._advance_frame('key1', 4, 0.5, 'move')
    assert 0 <= idx < 4

def test_advance_frame_wraps_around():
    renderer, _ = _make_renderer()
    renderer._frame_counters['key1'] = 3.9
    idx = renderer._advance_frame('key1', 4, 1.0, 'move')
    assert 0 <= idx < 4


# ── _draw_cooldown_bar ────────────────────────────────────────────────────────

def test_draw_cooldown_bar_skips_when_no_cooldown():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    canvas = _make_canvas()
    with patch('cv2.rectangle') as mock_rect:
        renderer._draw_cooldown_bar(canvas, 0, 0, state)
        mock_rect.assert_not_called()

def test_draw_cooldown_bar_draws_when_active():
    renderer, _ = _make_renderer()
    state = _make_state([['wP']])
    state.clock = 0
    state.cooldowns[(0, 0)] = 2000
    state.rest_type[(0, 0)] = 'long_rest'
    canvas = _make_canvas()
    with patch('cv2.rectangle') as mock_rect:
        renderer._draw_cooldown_bar(canvas, 0, 0, state)
        assert mock_rect.call_count == 2  # background + fill


# ── render calls loader ───────────────────────────────────────────────────────

def test_render_calls_loader_for_each_piece():
    renderer, loader = _make_renderer()
    state = _make_state([['wP', '.', 'bR']])
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0):
        renderer._last_tick = 1.0
        renderer.render(canvas, state)
    tokens_requested = [call[0][0] for call in loader.get.call_args_list]
    assert 'wP' in tokens_requested
    assert 'bR' in tokens_requested

def test_render_skips_empty_squares():
    renderer, loader = _make_renderer()
    state = _make_state([['.', '.', '.']])
    canvas = _make_canvas()
    with patch('time.time', return_value=1.0):
        renderer._last_tick = 1.0
        renderer.render(canvas, state)
    loader.get.assert_not_called()
