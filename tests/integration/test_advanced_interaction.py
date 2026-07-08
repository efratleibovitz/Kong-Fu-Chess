import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService


def test_enemy_collision_white_started_first():
    game = GameService(Board([['wR', '.', '.', 'bR']]))
    game.click(50, 50)
    game.click(350, 50)
    game.click(350, 50)
    game.click(50, 50)
    game.wait(3000)
    assert game.board.get_token(Position(3, 0)) == 'wR'
    assert game.board.get_token(Position(0, 0)) == '.'


def test_enemy_collision_black_started_first():
    game = GameService(Board([['wR', '.', '.', 'bR']]))
    game.click(350, 50)
    game.click(50, 50)
    game.click(50, 50)
    game.click(350, 50)
    game.wait(3000)
    assert game.board.get_token(Position(0, 0)) == 'bR'
    assert game.board.get_token(Position(3, 0)) == '.'


def test_cannot_start_move_through_friendly_piece():
    game = GameService(Board([['.', '.', '.'], ['wR', 'wP', '.'], ['.', '.', '.']]))
    game.click(50, 150)
    game.click(250, 150)
    game.wait(2000)
    assert game.board.get_token(Position(0, 1)) == 'wR'
    assert game.board.get_token(Position(1, 1)) == 'wP'


def test_dynamic_block_tactic_not_in_common_route():
    game = GameService(Board([
        ['.', '.', '.', '.'],
        ['wQ', '.', '.', 'bK'],
        ['.', '.', 'bP', '.'],
        ['.', '.', '.', '.'],
    ]))
    game.click(50, 150)
    game.click(350, 150)
    game.wait(200)
    game.click(250, 250)
    game.click(250, 150)
    game.wait(3000)
    assert game.board.get_token(Position(3, 1)) == 'wQ'
    assert game.board.get_token(Position(2, 2)) == 'bP'


def test_knight_cannot_land_on_friendly_piece():
    game = GameService(Board([['.', 'wP', '.'], ['.', '.', '.'], ['wN', '.', '.']]))
    game.click(50, 250)
    game.click(150, 50)
    game.wait(1000)
    assert game.board.get_token(Position(0, 2)) == 'wN'
    assert game.board.get_token(Position(1, 0)) == 'wP'


def test_premove_does_not_execute_in_common_route():
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    assert game.board.get_token(Position(1, 0)) == 'wR'
    assert game.board.get_token(Position(2, 0)) == '.'
