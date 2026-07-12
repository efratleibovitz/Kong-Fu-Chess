import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from model.board import Board
from model.position import Position
from input.board_mapper import BoardMapper

# --- BoardMapper: pixel_to_cell ---

def test_pixel_to_cell_center_of_first_cell():
    assert BoardMapper.pixel_to_cell(50, 50) == Position(0, 0)

def test_pixel_to_cell_center_of_second_cell():
    assert BoardMapper.pixel_to_cell(150, 50) == Position(1, 0)

def test_pixel_to_cell_out_of_bounds_returns_none():
    assert not BoardMapper.is_within_bounds(350, 50, num_cols=2, num_rows=2)

def test_pixel_to_cell_negative_returns_none():
    assert not BoardMapper.is_within_bounds(-10, 50, num_cols=2, num_rows=2)

# --- Board: get/set token ---

def test_get_and_set_token():
    board = Board([['wK', '.'], ['.', '.']])
    pos = Position(0, 0)
    board.set_token(pos, '.')
    assert board.get_token(pos) == '.'
