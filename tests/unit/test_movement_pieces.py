import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.model.board import Board
from core.model.position import Position
from core.rules.rule_engine import RuleEngine
from core.rules.moves.utils import is_blocked


def _empty(cols, rows):
    return Board([['.' for _ in range(cols)] for _ in range(rows)])


def _valid(board, from_pos, to_pos):
    return RuleEngine().validate_move(board, from_pos, to_pos)["is_valid"]


# ---------------------------------------------------------------------------
# KnightMove
# ---------------------------------------------------------------------------

def test_knight_valid_l_shapes():
    board = _empty(5, 5)
    board.set_token(Position(2, 2), 'wN')
    for dc, dr in [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]:
        assert _valid(board, Position(2, 2), Position(2 + dc, 2 + dr))


def test_knight_straight_move_is_invalid():
    board = _empty(5, 5)
    board.set_token(Position(2, 2), 'wN')
    assert not _valid(board, Position(2, 2), Position(2, 4))
    assert not _valid(board, Position(2, 2), Position(4, 2))


def test_knight_diagonal_move_is_invalid():
    board = _empty(5, 5)
    board.set_token(Position(2, 2), 'wN')
    assert not _valid(board, Position(2, 2), Position(4, 4))


def test_knight_one_step_is_invalid():
    board = _empty(5, 5)
    board.set_token(Position(2, 2), 'wN')
    assert not _valid(board, Position(2, 2), Position(3, 3))
    assert not _valid(board, Position(2, 2), Position(3, 2))


# ---------------------------------------------------------------------------
# QueenMove
# ---------------------------------------------------------------------------

def test_queen_straight_horizontal_valid():
    board = _empty(5, 5)
    board.set_token(Position(0, 2), 'wQ')
    assert _valid(board, Position(0, 2), Position(4, 2))


def test_queen_straight_vertical_valid():
    board = _empty(5, 5)
    board.set_token(Position(2, 0), 'wQ')
    assert _valid(board, Position(2, 0), Position(2, 4))


def test_queen_diagonal_valid():
    board = _empty(5, 5)
    board.set_token(Position(0, 0), 'wQ')
    assert _valid(board, Position(0, 0), Position(4, 4))


def test_queen_l_shape_invalid():
    board = _empty(5, 5)
    board.set_token(Position(2, 2), 'wQ')
    assert not _valid(board, Position(2, 2), Position(4, 3))


def test_queen_stay_in_place_invalid():
    board = _empty(5, 5)
    board.set_token(Position(2, 2), 'wQ')
    assert not _valid(board, Position(2, 2), Position(2, 2))


# ---------------------------------------------------------------------------
# RookMove
# ---------------------------------------------------------------------------

def test_rook_stay_in_place_invalid():
    board = _empty(3, 3)
    board.set_token(Position(1, 1), 'wR')
    assert not _valid(board, Position(1, 1), Position(1, 1))


# ---------------------------------------------------------------------------
# utils.is_blocked
# ---------------------------------------------------------------------------

def test_is_blocked_clear_path():
    board = Board([['wR', '.', '.', '.']])
    assert not is_blocked(Position(0, 0), Position(3, 0), board)


def test_is_blocked_piece_in_middle():
    board = Board([['wR', 'bP', '.', '.']])
    assert is_blocked(Position(0, 0), Position(3, 0), board)


def test_is_blocked_adjacent_squares_never_blocked():
    board = Board([['wR', 'bP']])
    # no squares between adjacent positions — loop never runs
    assert not is_blocked(Position(0, 0), Position(1, 0), board)


def test_is_blocked_diagonal_clear():
    board = Board([['.', '.', '.'], ['.', '.', '.'], ['wB', '.', '.']])
    assert not is_blocked(Position(0, 2), Position(2, 0), board)


def test_is_blocked_diagonal_blocked():
    board = Board([['.', '.', '.'], ['.', 'wP', '.'], ['wB', '.', '.']])
    assert is_blocked(Position(0, 2), Position(2, 0), board)
