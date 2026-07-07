import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import importlib
from io import StringIO
from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService

# --- Board tests ---

def test_pixel_to_cell_center_of_first_cell():
    # Verifies that clicking the center of the top-left cell (50,50) maps to position (0,0)
    board = Board([['wK', '.'], ['.', '.']])
    assert board.pixel_to_cell(50, 50) == Position(0, 0)

def test_pixel_to_cell_center_of_second_cell():
    # Verifies that clicking pixel (150,50) maps to column 1, row 0
    board = Board([['wK', '.'], ['.', '.']])
    assert board.pixel_to_cell(150, 50) == Position(1, 0)

def test_pixel_to_cell_out_of_bounds_returns_none():
    # Verifies that a pixel outside the board boundaries returns None
    board = Board([['wK', '.'], ['.', '.']])
    assert board.pixel_to_cell(350, 50) is None

def test_pixel_to_cell_negative_returns_none():
    # Verifies that a negative pixel coordinate returns None
    board = Board([['wK', '.'], ['.', '.']])
    assert board.pixel_to_cell(-10, 50) is None

def test_get_and_set_token():
    # Verifies that set_token correctly updates the cell and get_token reads it back
    board = Board([['wK', '.'], ['.', '.']])
    pos = Position(0, 0)
    board.set_token(pos, '.')
    assert board.get_token(pos) == '.'

def test_print_board_output(capsys):
    # Verifies that print() outputs each row as space-separated tokens
    board = Board([['wK', '.'], ['.', 'bK']])
    board.print()
    captured = capsys.readouterr()
    assert captured.out == 'wK .\n. bK\n'

# --- GameService tests ---

def test_click_piece_selects_it():
    # Verifies that clicking on a cell with a piece sets it as the selected piece
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    assert game.selected == Position(0, 0)

def test_click_empty_cell_without_selection_does_nothing():
    # Verifies that clicking an empty cell when nothing is selected leaves selected as None
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(150, 50)
    assert game.selected is None

def test_click_empty_cell_after_selection_schedules_move():
    # Verifies that clicking an empty cell after selecting a piece schedules a pending move
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    assert len(game.pending_moves) == 1
    assert game.selected is None

def test_piece_stays_at_source_until_arrival():
    # Verifies that the source cell still shows the piece while the move is in transit
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    assert game.board.get_token(Position(0, 0)) == 'wK'
    assert game.board.get_token(Position(1, 0)) == '.'

def test_wait_settles_move_after_1000ms():
    # Verifies that after waiting 1000ms a 1-cell king move appears at the destination
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    game.wait(1000)
    assert game.board.get_token(Position(1, 0)) == 'wK'
    assert len(game.pending_moves) == 0

def test_wait_does_not_settle_move_before_1000ms():
    # Verifies that waiting less than 500ms does not place a 1-cell piece at the destination
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(50, 50)
    game.click(150, 50)
    game.wait(400)
    assert game.board.get_token(Position(1, 0)) == '.'
    assert len(game.pending_moves) == 1

def test_two_cell_move_arrives_after_2000ms():
    # Verifies that a 2-cell rook move takes 1000ms to arrive (distance * 500)
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(500)
    assert game.board.get_token(Position(2, 0)) == '.'
    game.wait(500)
    assert game.board.get_token(Position(2, 0)) == 'wR'

def test_two_cell_move_not_arrived_after_1000ms():
    # Verifies that a 2-cell rook move is still in transit after 400ms — piece visible at origin, not yet at destination
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(400)
    assert game.board.get_token(Position(0, 0)) == 'wR'
    assert game.board.get_token(Position(2, 0)) == '.'

def test_moving_piece_cannot_be_redirected():
    # Verifies that a piece in transit arrives at original destination even if clicks happen after
    game = GameService(Board([['wR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(1000)
    game.click(150, 50)  # click mid-cell while piece is in transit, nothing selected
    game.wait(1000)
    assert game.board.get_token(Position(2, 0)) == 'wR'

def test_clicking_another_piece_replaces_selection():
    # Verifies that clicking a second piece while one is already selected replaces the selection
    game = GameService(Board([['wR', '.', 'wK'], ['.', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    assert game.selected == Position(2, 0)

def test_click_outside_board_is_ignored():
    # Verifies that clicking outside the board boundaries does not change game state
    game = GameService(Board([['wK', '.'], ['.', '.']]))
    game.click(350, 50)
    assert game.selected is None

# --- main.py integration tests ---

def test_main_select_and_move(capsys, monkeypatch):
    # Verifies the full flow: select piece, click destination, wait, print shows piece moved
    input_text = 'Board:\nwK . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 150 150\nwait 1000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . .\n. wK .\n. . .'

def test_main_error_unknown_token(capsys, monkeypatch):
    # Verifies that an unknown token in the board triggers ERROR UNKNOWN_TOKEN output
    input_text = 'Board:\nwK xZ\n. .\nCommands:\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == 'ERROR UNKNOWN_TOKEN'

def test_main_error_row_width_mismatch(capsys, monkeypatch):
    # Verifies that rows of different widths trigger ERROR ROW_WIDTH_MISMATCH output
    input_text = 'Board:\nwK . .\n. bK\nCommands:\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == 'ERROR ROW_WIDTH_MISMATCH'
