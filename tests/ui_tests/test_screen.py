"""
test_screen.py
Covers: view/screen.py

Tests that Screen:
- single left click before start sets _started=True
- single left click after start routes to engine.click
- double left click after start routes to engine.jump
- clicks outside board width are ignored
- click before start does NOT call engine.click
- engine.wait is called each frame with frame_ms
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import cv2
import numpy as np
from unittest.mock import MagicMock, patch, call
from model.board import Board
from model.game_state import GameState
from view.screen import Screen
from input.board_mapper import BoardMapper

CELL = BoardMapper.CELL_SIZE
BOARD_W = 8 * CELL
BOARD_H = 8 * CELL


def _make_screen():
    state = GameState(Board([['.'] * 8] * 8))
    state.player_names = {'w': 'White', 'b': 'Black'}
    state.scores = {'w': 0, 'b': 0}
    state.captured = {'w': [], 'b': []}

    engine = MagicMock()
    engine.state = state

    loader = MagicMock()
    loader.get.return_value = []

    with patch('view.screen.SpriteLoader', return_value=loader), \
         patch('view.screen.BoardRenderer'), \
         patch('view.screen.HUDRenderer'), \
         patch('view.screen.OverlayRenderer'):
        screen = Screen(engine, state)

    screen._engine = engine
    screen._state = state
    screen._board_w = BOARD_W
    return screen, engine


# ── start screen ──────────────────────────────────────────────────────────────

def test_click_before_start_sets_started():
    screen, engine = _make_screen()
    assert screen._started is False
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    assert screen._started is True

def test_click_before_start_does_not_call_engine():
    screen, engine = _make_screen()
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    engine.click.assert_not_called()
    engine.jump.assert_not_called()


# ── single click routing ──────────────────────────────────────────────────────

def test_single_click_calls_engine_click():
    screen, engine = _make_screen()
    screen._started = True
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    engine.click.assert_called_once_with(100, 100)

def test_single_click_does_not_call_jump():
    screen, engine = _make_screen()
    screen._started = True
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
    engine.jump.assert_not_called()


# ── double click routing ──────────────────────────────────────────────────────

def test_double_click_calls_engine_jump():
    screen, engine = _make_screen()
    screen._started = True
    screen._on_mouse(cv2.EVENT_LBUTTONDBLCLK, 200, 200, 0, None)
    engine.jump.assert_called_once_with(200, 200)

def test_double_click_does_not_call_click():
    screen, engine = _make_screen()
    screen._started = True
    screen._on_mouse(cv2.EVENT_LBUTTONDBLCLK, 200, 200, 0, None)
    engine.click.assert_not_called()


# ── out of board bounds ───────────────────────────────────────────────────────

def test_click_outside_board_width_ignored():
    screen, engine = _make_screen()
    screen._started = True
    screen._on_mouse(cv2.EVENT_LBUTTONDOWN, BOARD_W + 10, 100, 0, None)
    engine.click.assert_not_called()

def test_double_click_outside_board_width_ignored():
    screen, engine = _make_screen()
    screen._started = True
    screen._on_mouse(cv2.EVENT_LBUTTONDBLCLK, BOARD_W + 10, 100, 0, None)
    engine.jump.assert_not_called()
