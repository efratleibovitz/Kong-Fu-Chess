import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from core.Entities.position import Position
from core.Entities.board import Board
from core.movement_validator import is_valid_move

def _empty_board(cols, rows):
    return Board([['.' for _ in range(cols)] for _ in range(rows)])

# --- King ---

def test_king_one_step_any_direction_is_valid():
    # Verifies that the king can move exactly one step in any of the 8 directions
    board = _empty_board(5, 5)
    for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
        assert is_valid_move('wK', Position(2, 2), Position(2+dx, 2+dy), board)

def test_king_two_steps_is_invalid():
    # Verifies that the king cannot move two cells in any direction
    board = _empty_board(5, 5)
    assert not is_valid_move('wK', Position(0, 0), Position(2, 2), board)
    assert not is_valid_move('wK', Position(0, 0), Position(2, 0), board)

# --- Rook ---

def test_rook_straight_horizontal_is_valid():
    # Verifies that the rook can move any number of cells horizontally on an empty board
    board = _empty_board(3, 1)
    assert is_valid_move('wR', Position(0, 0), Position(2, 0), board)

def test_rook_straight_vertical_is_valid():
    # Verifies that the rook can move any number of cells vertically on an empty board
    board = _empty_board(1, 4)
    assert is_valid_move('wR', Position(0, 0), Position(0, 3), board)

def test_rook_diagonal_is_invalid():
    # Verifies that the rook cannot move diagonally
    board = _empty_board(3, 3)
    assert not is_valid_move('wR', Position(0, 0), Position(1, 1), board)

def test_rook_blocked_by_own_piece():
    # Verifies that a rook cannot move through a friendly piece in its path
    board = Board([['wR', 'wP', '.']])
    assert not is_valid_move('wR', Position(0, 0), Position(2, 0), board)

def test_rook_captures_enemy_at_destination():
    # Verifies that a rook can move to a square occupied by an enemy piece
    board = Board([['wR', '.', 'bR']])
    assert is_valid_move('wR', Position(0, 0), Position(2, 0), board)

def test_cannot_capture_own_piece():
    # Verifies that a rook cannot move to a square occupied by a friendly piece
    board = Board([['wR', '.', 'wP']])
    assert not is_valid_move('wR', Position(0, 0), Position(2, 0), board)

# --- Bishop ---

def test_bishop_diagonal_is_valid():
    # Verifies that the bishop can move any number of cells diagonally on an empty board
    board = _empty_board(3, 3)
    assert is_valid_move('wB', Position(0, 0), Position(2, 2), board)

def test_bishop_straight_is_invalid():
    # Verifies that the bishop cannot move in a straight line
    board = _empty_board(3, 3)
    assert not is_valid_move('wB', Position(0, 0), Position(2, 0), board)
    assert not is_valid_move('wB', Position(0, 0), Position(0, 2), board)

def test_bishop_staying_in_place_is_invalid():
    # Verifies that dx==dy==0 (no movement) is not accepted as a valid bishop move
    board = _empty_board(3, 3)
    assert not is_valid_move('wB', Position(1, 1), Position(1, 1), board)

def test_bishop_blocked_by_own_piece():
    # Verifies that a bishop cannot move through a friendly piece on its diagonal path
    board = Board([['wB', '.', '.'], ['.', 'wP', '.'], ['.', '.', '.']])
    assert not is_valid_move('wB', Position(0, 0), Position(2, 2), board)

# --- Queen ---

def test_queen_straight_is_valid():
    # Verifies that the queen can move straight like a rook on an empty board
    board = _empty_board(4, 4)
    assert is_valid_move('wQ', Position(0, 0), Position(0, 3), board)
    assert is_valid_move('wQ', Position(0, 0), Position(3, 0), board)

def test_queen_diagonal_is_valid():
    # Verifies that the queen can move diagonally like a bishop on an empty board
    board = _empty_board(3, 3)
    assert is_valid_move('wQ', Position(0, 0), Position(2, 2), board)

def test_queen_L_shape_is_invalid():
    # Verifies that the queen cannot make an L-shaped knight move
    board = _empty_board(3, 3)
    assert not is_valid_move('wQ', Position(0, 0), Position(1, 2), board)

# --- Knight ---

def test_knight_L_shape_is_valid():
    # Verifies that the knight can make all valid L-shaped moves on an empty board
    board = _empty_board(5, 5)
    for dx, dy in [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]:
        assert is_valid_move('wN', Position(2, 2), Position(2+dx, 2+dy), board)

def test_knight_straight_is_invalid():
    # Verifies that the knight cannot move in a straight line
    board = _empty_board(3, 3)
    assert not is_valid_move('wN', Position(0, 0), Position(2, 0), board)

def test_knight_diagonal_is_invalid():
    # Verifies that the knight cannot move diagonally
    board = _empty_board(3, 3)
    assert not is_valid_move('wN', Position(0, 0), Position(2, 2), board)

def test_knight_jumps_over_blockers():
    # Verifies that a knight can jump over pieces blocking its path
    board = Board([['wN', 'wP', '.'], ['wP', '.', '.'], ['.', '.', '.']])
    assert is_valid_move('wN', Position(0, 0), Position(1, 2), board)

# --- Pawn ---

def test_white_pawn_moves_forward_one_step():
    # Verifies that a white pawn can move one step upward (decreasing row) to an empty cell
    board = Board([['.', '.', '.'], ['.', 'wP', '.'], ['.', '.', '.']])
    assert is_valid_move('wP', Position(1, 1), Position(1, 0), board)

def test_black_pawn_moves_forward_one_step():
    # Verifies that a black pawn can move one step downward (increasing row) to an empty cell
    board = Board([['.', '.', '.'], ['.', 'bP', '.'], ['.', '.', '.']])
    assert is_valid_move('bP', Position(1, 1), Position(1, 2), board)

def test_white_pawn_cannot_move_backward():
    # Verifies that a white pawn cannot move downward (wrong direction)
    board = Board([['.', '.', '.'], ['.', 'wP', '.'], ['.', '.', '.']])
    assert not is_valid_move('wP', Position(1, 1), Position(1, 2), board)

def test_black_pawn_cannot_move_backward():
    # Verifies that a black pawn cannot move upward (wrong direction)
    board = Board([['.', '.', '.'], ['.', 'bP', '.'], ['.', '.', '.']])
    assert not is_valid_move('bP', Position(1, 1), Position(1, 0), board)

def test_pawn_cannot_move_forward_if_blocked():
    # Verifies that a pawn cannot move forward if the destination cell is occupied
    board = Board([['bR', '.', '.'], ['wP', '.', '.'], ['.', '.', '.']])
    assert not is_valid_move('wP', Position(0, 1), Position(0, 0), board)

def test_pawn_double_step_is_invalid():
    # Verifies that a pawn cannot move two steps forward under any circumstance
    board = Board([['.', '.', '.'], ['.', '.', '.'], ['.', 'wP', '.'], ['.', '.', '.']])
    assert not is_valid_move('wP', Position(1, 2), Position(1, 0), board)

def test_white_pawn_captures_diagonally():
    # Verifies that a white pawn can capture an enemy piece one step diagonally forward
    board = Board([['bR', '.', '.'], ['.', 'wP', '.'], ['.', '.', '.']])
    assert is_valid_move('wP', Position(1, 1), Position(0, 0), board)

def test_pawn_cannot_capture_forward():
    # Verifies that a pawn cannot capture an enemy piece directly in front of it
    board = Board([['.', 'bR', '.'], ['.', 'wP', '.'], ['.', '.', '.']])
    assert not is_valid_move('wP', Position(1, 1), Position(1, 0), board)

def test_pawn_cannot_capture_empty_diagonal():
    # Verifies that a pawn cannot move diagonally if the destination is empty (no capture target)
    board = Board([['.', '.', '.'], ['.', 'wP', '.'], ['.', '.', '.']])
    assert not is_valid_move('wP', Position(1, 1), Position(0, 0), board)
