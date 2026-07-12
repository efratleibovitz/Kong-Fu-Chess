import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from model.board import Board
from model.position import Position
from model.game_state import GameState
from engine.game_engine import GameEngine


def _make(rows):
    return GameEngine(GameState(Board(rows)))


def test_king_capture_sets_game_over():
    game = _make([['wR', '.', 'bK']])
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    assert game.game_over is True


def test_king_capture_ends_game():
    game = _make([['wR', '.', 'bK']])
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    assert game.board.get_token(Position(2, 0)) == 'wR'
    assert game.board.get_token(Position(0, 0)) == '.'


def test_no_moves_after_game_over():
    game = _make([['wR', '.', 'bK'], ['bR', '.', '.']])
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    game.click(50, 150)
    game.click(150, 150)
    game.wait(1000)
    assert game.board.get_token(Position(0, 1)) == 'bR'
    assert game.board.get_token(Position(1, 1)) == '.'


def test_click_ignored_after_game_over():
    game = _make([['wR', '.', 'bK']])
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    game.click(50, 50)
    assert game.selected is None


def test_wait_ignored_after_game_over():
    game = _make([['wR', '.', 'bK'], ['bR', '.', '.']])
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    game.click(50, 150)
    game.click(150, 150)
    game.wait(1000)
    assert game.board.get_token(Position(0, 1)) == 'bR'
    assert game.board.get_token(Position(1, 1)) == '.'
