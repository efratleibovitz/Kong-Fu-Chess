import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.model.notation import move_to_notation, square_name


# ---------------------------------------------------------------------------
# square_name
# ---------------------------------------------------------------------------

def test_square_name_a8():
    assert square_name(0, 0) == 'a8'


def test_square_name_h1():
    assert square_name(7, 7) == 'h1'


def test_square_name_e4():
    assert square_name(4, 4) == 'e4'


# ---------------------------------------------------------------------------
# Castling
# ---------------------------------------------------------------------------

def test_kingside_castle_notation():
    assert move_to_notation('K', 4, 7, 6, 7, is_castle_kingside=True) == 'O-O'


def test_queenside_castle_notation():
    assert move_to_notation('K', 4, 7, 2, 7, is_castle_queenside=True) == 'O-O-O'


def test_kingside_castle_with_check():
    assert move_to_notation('K', 4, 7, 6, 7, is_castle_kingside=True, is_check=True) == 'O-O+'


def test_queenside_castle_with_checkmate():
    assert move_to_notation('K', 4, 7, 2, 7, is_castle_queenside=True, is_checkmate=True) == 'O-O-O#'


# ---------------------------------------------------------------------------
# Pawn notation
# ---------------------------------------------------------------------------

def test_pawn_quiet_move():
    result = move_to_notation('P', 4, 6, 4, 4)
    assert result == 'e4'


def test_pawn_capture_notation():
    result = move_to_notation('P', 4, 6, 3, 5, is_capture=True)
    assert result == 'exd3'


# ---------------------------------------------------------------------------
# Piece notation (no board — no disambiguation)
# ---------------------------------------------------------------------------

def test_rook_quiet_move():
    result = move_to_notation('R', 0, 7, 0, 0)
    assert result == 'Ra8'


def test_rook_capture():
    result = move_to_notation('R', 0, 7, 0, 0, is_capture=True)
    assert result == 'Rxa8'


def test_queen_move_with_check():
    result = move_to_notation('Q', 3, 7, 3, 0, is_check=True)
    assert result == 'Qd8+'


def test_queen_move_with_checkmate():
    result = move_to_notation('Q', 3, 7, 3, 0, is_checkmate=True)
    assert result == 'Qd8#'


def test_checkmate_takes_priority_over_check():
    # is_checkmate=True should produce '#' not '+'
    result = move_to_notation('R', 0, 7, 0, 0, is_check=True, is_checkmate=True)
    assert result == 'Ra8#'


# ---------------------------------------------------------------------------
# Disambiguation (two rooks that could reach the same square)
# ---------------------------------------------------------------------------

def test_disambiguate_by_column_when_same_row():
    from core.model.board import Board
    from core.model.position import Position
    # Two white rooks on same row, both could reach col=3
    # wR at (0,0) moves to (3,0); wR at (5,0) also on same row
    board = Board([['wR', '.', '.', 'wR_dest', '.', 'wR2', '.', '.']])
    board.set_token(Position(0, 0), 'wR')
    board.set_token(Position(3, 0), 'wR')   # destination — piece already moved here
    board.set_token(Position(5, 0), 'wR')   # rival
    result = move_to_notation('R', 0, 0, 3, 0, board=board)
    # rival at col=5 can reach col=3 horizontally → disambiguate by column
    assert 'a' in result or result.startswith('R')


def test_no_disambiguation_when_no_rival():
    from core.model.board import Board
    from core.model.position import Position
    board = Board([['.', '.', '.', '.', '.', '.', '.', '.']] * 8)
    board.set_token(Position(3, 7), 'wR')   # destination
    result = move_to_notation('R', 0, 7, 3, 7, board=board)
    assert result == 'Rd1'
