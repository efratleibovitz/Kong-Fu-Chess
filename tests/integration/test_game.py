import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService


def test_click_piece_selects_it():
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    assert game.selected == Position(0, 0)


def test_click_empty_cell_without_selection_does_nothing():
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(150, 50)
    assert game.selected is None


def test_click_empty_cell_after_selection_schedules_move():
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    assert len(game.pending_moves) == 1
    assert game.selected is None


def test_piece_stays_at_source_until_arrival():
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    assert game.board.get_token(Position(0, 0)) == 'wK'
    assert game.board.get_token(Position(1, 0)) == '.'


def test_wait_settles_move_after_1000ms():
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    game.wait(1000)
    assert game.board.get_token(Position(1, 0)) == 'wK'
    assert len(game.pending_moves) == 0


def test_wait_does_not_settle_move_before_1000ms():
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    game.wait(400)
    assert game.board.get_token(Position(1, 0)) == '.'
    assert len(game.pending_moves) == 1


def test_two_cell_move_arrives_after_2000ms():
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(500)
    assert game.board.get_token(Position(2, 0)) == '.'
    game.wait(500)
    assert game.board.get_token(Position(2, 0)) == 'wR'


def test_two_cell_move_not_arrived_after_1000ms():
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(400)
    assert game.board.get_token(Position(0, 0)) == 'wR'
    assert game.board.get_token(Position(2, 0)) == '.'


def test_moving_piece_cannot_be_redirected():
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(1000)
    game.click(150, 50)
    game.wait(1000)
    assert game.board.get_token(Position(2, 0)) == 'wR'


def test_clicking_another_piece_replaces_selection():
    game = GameService(Board([['wR', '.', 'wK'], ['.', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    assert game.selected == Position(2, 0)


def test_click_outside_board_is_ignored():
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(350, 50)
    assert game.selected is None


def test_print_board_outputs_board(capsys):
    game = GameService(Board([['wK', '.'], ['.', 'bK']]))
    game.print_board()
    captured = capsys.readouterr()
    assert captured.out == 'wK .\n. bK\n'
