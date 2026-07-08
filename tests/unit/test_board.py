import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from core.Entities.board import Board
from core.Entities.position import Position

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
