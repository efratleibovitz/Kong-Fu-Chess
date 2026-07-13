import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from model.board import Board
from model.position import Position
from rules.rule_engine import RuleEngine

def _empty_board(cols, rows):
    return Board([['.' for _ in range(cols)] for _ in range(rows)])

def _is_valid(board, from_pos, to_pos):
    return RuleEngine().validate_move(board, from_pos, to_pos)["is_valid"]

# --- King ---

def test_king_one_step_any_direction_is_valid():
    board = _empty_board(5, 5)
    for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
        board.set_token(Position(2, 2), 'wK')
        assert _is_valid(board, Position(2, 2), Position(2+dx, 2+dy))

def test_king_two_steps_is_invalid():
    board = _empty_board(5, 5)
    board.set_token(Position(0, 0), 'wK')
    assert not _is_valid(board, Position(0, 0), Position(2, 2))
    assert not _is_valid(board, Position(0, 0), Position(2, 0))

# --- Rook ---

def test_rook_straight_horizontal_is_valid():
    board = _empty_board(3, 1)
    board.set_token(Position(0, 0), 'wR')
    assert _is_valid(board, Position(0, 0), Position(2, 0))

def test_rook_straight_vertical_is_valid():
    board = _empty_board(1, 4)
    board.set_token(Position(0, 0), 'wR')
    assert _is_valid(board, Position(0, 0), Position(0, 3))

def test_rook_diagonal_is_invalid():
    board = _empty_board(3, 3)
    board.set_token(Position(0, 0), 'wR')
    assert not _is_valid(board, Position(0, 0), Position(1, 1))

# def test_rook_blocked_by_own_piece():
#     board = Board([['wR', 'wP', '.']])
#     assert not _is_valid(board, Position(0, 0), Position(2, 0))

def test_rook_geometry_valid_even_with_own_piece_on_path():
    # RuleEngine validates geometric legality + friendly-destination only.
    # Mid-path blocking by a friendly piece is handled later by MoveScheduler's
    # path walk (see tests/integration/test_collision.py::
    # test_rook_stops_one_before_friendly_mid_path), not by RuleEngine.
    board = Board([['wR', 'wP', '.']])
    assert _is_valid(board, Position(0, 0), Position(2, 0))
    
def test_rook_captures_enemy_at_destination():
    board = Board([['wR', '.', 'bR']])
    assert _is_valid(board, Position(0, 0), Position(2, 0))

def test_cannot_capture_own_piece():
    board = Board([['wR', '.', 'wP']])
    assert not _is_valid(board, Position(0, 0), Position(2, 0))

# --- Bishop ---

def test_bishop_diagonal_is_valid():
    board = _empty_board(3, 3)
    board.set_token(Position(0, 0), 'wB')
    assert _is_valid(board, Position(0, 0), Position(2, 2))

def test_bishop_straight_is_invalid():
    board = _empty_board(3, 3)
    board.set_token(Position(0, 0), 'wB')
    assert not _is_valid(board, Position(0, 0), Position(2, 0))
    assert not _is_valid(board, Position(0, 0), Position(0, 2))

def test_bishop_staying_in_place_is_invalid():
    board = _empty_board(3, 3)
    board.set_token(Position(1, 1), 'wB')
    assert not _is_valid(board, Position(1, 1), Position(1, 1))
