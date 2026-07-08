import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService


def test_white_pawn_promotes_to_queen_on_arrival():
    game = GameService(Board([['.', '.'], ['.', 'wP']]))
    game.click(150, 150)
    game.click(150, 50)
    game.wait(1000)
    assert game.board.get_token(Position(1, 0)) == 'wQ'


def test_black_pawn_promotes_to_queen_on_arrival():
    game = GameService(Board([['.', 'bP'], ['.', '.']]))
    game.click(150, 50)
    game.click(150, 150)
    game.wait(1000)
    assert game.board.get_token(Position(1, 1)) == 'bQ'


def test_promoted_queen_can_move_diagonally():
    game = GameService(Board([['.', '.', '.'], ['.', 'wP', '.'], ['.', '.', '.']]))
    game.click(150, 150)
    game.click(150, 50)
    game.wait(1000)
    game.click(150, 50)
    game.click(250, 150)
    game.wait(1000)
    assert game.board.get_token(Position(2, 1)) == 'wQ'


def test_white_pawn_double_step_arrives_correctly():
    game = GameService(Board([
        ['.', '.', '.'],
        ['.', '.', '.'],
        ['.', '.', '.'],
        ['.', 'wP', '.'],
    ]))
    game.click(150, 350)
    game.click(150, 150)
    game.wait(2000)
    assert game.board.get_token(Position(1, 1)) == 'wP'
    assert game.board.get_token(Position(1, 3)) == '.'
