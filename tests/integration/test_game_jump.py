import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService


def test_jump_lands_same_square():
    game = GameService(Board([['.', '.', '.'], ['.', 'wK', '.'], ['.', '.', '.']]))
    game.jump(150, 150)
    game.wait(1000)
    assert game.board.get_token(Position(1, 1)) == 'wK'


def test_airborne_piece_captures_arriving_enemy():
    game = GameService(Board([['.', '.', '.'], ['wK', '.', 'bR'], ['.', '.', '.']]))
    game.jump(50, 150)
    game.click(250, 150)
    game.click(50, 150)
    game.wait(1000)
    assert game.board.get_token(Position(0, 1)) == 'wK'
    assert game.board.get_token(Position(2, 1)) == '.'


def test_jump_too_late_does_not_save_piece():
    game = GameService(Board([['.', '.', '.'], ['wK', '.', 'bR'], ['.', '.', '.']]))
    game.click(250, 150)
    game.click(50, 150)
    game.wait(1000)
    game.jump(50, 150)
    assert game.board.get_token(Position(0, 1)) == 'bR'
    assert game.board.get_token(Position(2, 1)) == '.'


def test_enemy_arrives_after_landing_captures_normally():
    game = GameService(Board([['.', '.', '.', '.'], ['wK', '.', '.', 'bR'], ['.', '.', '.', '.']]))
    game.jump(50, 150)
    game.wait(1000)
    game.click(350, 150)
    game.click(50, 150)
    game.wait(3000)
    assert game.board.get_token(Position(0, 1)) == 'bR'
    assert game.board.get_token(Position(3, 1)) == '.'


def test_cannot_jump_while_moving():
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(500)
    game.jump(50, 50)
    game.wait(1500)
    assert game.board.get_token(Position(2, 0)) == 'wR'
    assert game.board.get_token(Position(0, 0)) == '.'


def test_airborne_capture_only_enemy():
    game = GameService(Board([['.', '.', '.'], ['wK', '.', 'wR'], ['.', '.', '.']]))
    game.jump(50, 150)
    game.click(250, 150)
    game.click(50, 150)
    game.wait(1000)
    assert game.board.get_token(Position(0, 1)) == 'wK'
    assert game.board.get_token(Position(2, 1)) == 'wR'


def test_jump_out_of_bounds_is_ignored():
    game = GameService(Board([['.', '.', '.'], ['.', 'wK', '.'], ['.', '.', '.']]))
    game.jump(9999, 9999)
    game.wait(1000)
    assert game.board.get_token(Position(1, 1)) == 'wK'
    assert len(game.pending_jumps) == 0


def test_intercepted_move_removes_source_piece():
    game = GameService(Board([['.', '.', '.'], ['wR', '.', 'bR'], ['.', '.', '.']]))
    game.jump(250, 150)
    game.click(50, 150)
    game.click(250, 150)
    game.wait(1000)
    assert game.board.get_token(Position(0, 1)) == '.'
    assert game.board.get_token(Position(2, 1)) == 'bR'
