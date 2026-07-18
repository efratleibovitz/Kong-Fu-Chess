"""
test_screen.py
Covers: view/screen.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import cv2
from unittest.mock import MagicMock, patch
from model.board import Board
from model.game_state import GameState
from view.screen import Screen
from input.board_mapper import BoardMapper

CELL = BoardMapper.CELL_SIZE
BOARD_W = 8 * CELL


def _make_screen():
    state = GameState(Board([['.'] * 8] * 8))
    state.player_names = {'w': 'White', 'b': 'Black'}
    state.scores = {'w': 0, 'b': 0}
    state.captured = {'w': [], 'b': []}

    engine = MagicMock()
    engine.state = state

    with patch('view.screen.SpriteLoader'), \
         patch('view.screen.BoardRenderer'), \
         patch('view.screen.HUDRenderer'), \
         patch('view.screen.OverlayRenderer'):
        screen = Screen(engine, state)

    screen._engine = engine
    screen._state = state
    screen._board_w = BOARD_W
    return screen, engine, state


# ── start screen ──────────────────────────────────────────────────────────────

def test_click_before_start_sets_started():
    screen, engine, _ = _make_screen()
    assert screen._started is False
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    assert screen._started is True

def test_click_before_start_marks_needs_redraw():
    screen, engine, _ = _make_screen()
    screen._needs_redraw = False
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    assert screen._needs_redraw is True

def test_click_before_start_does_not_call_engine():
    screen, engine, _ = _make_screen()
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    engine.click.assert_not_called()
    engine.jump.assert_not_called()


# ── single click routing ──────────────────────────────────────────────────────

def test_single_click_calls_engine_click():
    screen, engine, _ = _make_screen()
    screen._started = True
    with patch('cv2.getWindowImageRect', return_value=(0, 0, 0, 0)):
        screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    engine.click.assert_called_once_with(100, 100)

def test_single_click_does_not_call_jump():
    screen, engine, _ = _make_screen()
    screen._started = True
    with patch('cv2.getWindowImageRect', return_value=(0, 0, 0, 0)):
        screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    engine.jump.assert_not_called()


# ── double click routing ──────────────────────────────────────────────────────

def test_double_click_calls_engine_jump():
    screen, engine, _ = _make_screen()
    screen._started = True
    with patch('cv2.getWindowImageRect', return_value=(0, 0, 0, 0)):
        screen._on_mouse(cv2.EVENT_LBUTTONDBLCLK, 200, 200, 0, None)
    engine.jump.assert_called_once_with(200, 200)

def test_double_click_does_not_call_click():
    screen, engine, _ = _make_screen()
    screen._started = True
    with patch('cv2.getWindowImageRect', return_value=(0, 0, 0, 0)):
        screen._on_mouse(cv2.EVENT_LBUTTONDBLCLK, 200, 200, 0, None)
    engine.click.assert_not_called()


# ── out of board bounds ───────────────────────────────────────────────────────

def test_click_outside_board_width_ignored():
    screen, engine, _ = _make_screen()
    screen._started = True
    with patch('cv2.getWindowImageRect', return_value=(0, 0, 0, 0)):
        screen._on_mouse(cv2.EVENT_LBUTTONDOWN, BOARD_W + 10, 100, 0, None)
    engine.click.assert_not_called()

def test_double_click_outside_board_width_ignored():
    screen, engine, _ = _make_screen()
    screen._started = True
    with patch('cv2.getWindowImageRect', return_value=(0, 0, 0, 0)):
        screen._on_mouse(cv2.EVENT_LBUTTONDBLCLK, BOARD_W + 10, 100, 0, None)
    engine.jump.assert_not_called()


# ── observer / event subscriptions ───────────────────────────────────────────

def test_piece_settled_marks_needs_redraw():
    screen, _, state = _make_screen()
    screen._needs_redraw = False
    state.events.emit('piece_settled')
    assert screen._needs_redraw is True

def test_selection_changed_marks_needs_redraw():
    screen, _, state = _make_screen()
    screen._needs_redraw = False
    state.events.emit('selection_changed')
    assert screen._needs_redraw is True

def test_game_over_marks_needs_redraw():
    screen, _, state = _make_screen()
    screen._needs_redraw = False
    state.events.emit('game_over')
    assert screen._needs_redraw is True

def test_restarted_resets_started_and_marks_needs_redraw():
    screen, _, state = _make_screen()
    screen._started = True
    screen._needs_redraw = False
    state.events.emit('restarted')
    assert screen._started is False
    assert screen._needs_redraw is True
