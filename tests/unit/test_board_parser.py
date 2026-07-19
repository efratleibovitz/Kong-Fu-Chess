import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from iofiles.board_parser import parse_input, validate_board

def test_parse_input_separates_board_and_commands():
    # Verifies that board lines and command lines are correctly split into two separate lists
    lines = ['Board:\n', 'wK . bK\n', '. . .\n', 'Commands:\n', 'print board\n']
    board_lines, command_lines = parse_input(lines)
    assert board_lines == ['wK . bK', '. . .']
    assert command_lines == ['print board']

def test_parse_input_empty_commands():
    # Verifies that when Commands section has no entries, command list comes back empty
    lines = ['Board:\n', 'wK .\n', 'Commands:\n']
    board_lines, command_lines = parse_input(lines)
    assert command_lines == []

def test_validate_board_valid_3x4():
    # Verifies that a valid 3-row by 4-column board returns rows with no error
    board_lines = ['wK . . bK', '. . . .', 'wR . . bR']
    rows, error = validate_board(board_lines)
    assert error is None
    assert len(rows) == 3
    assert len(rows[0]) == 4

def test_validate_board_valid_pieces_and_empty():
    # Verifies that all valid piece tokens and empty squares pass validation
    board_lines = ['wK . bQ', '. wN .', 'bP . wR']
    rows, error = validate_board(board_lines)
    assert error is None
    assert rows[0][0].token == 'wK'
    assert rows[0][1] is None
    assert rows[0][2].token == 'bQ'

def test_validate_board_unknown_token():
    # Verifies that a token not matching [wb][KQRBNP] or . triggers UNKNOWN_TOKEN error
    board_lines = ['wK xZ', '. .']
    rows, error = validate_board(board_lines)
    assert error == 'UNKNOWN_TOKEN'
    assert rows is None

def test_validate_board_row_width_mismatch():
    # Verifies that rows with different number of tokens trigger ROW_WIDTH_MISMATCH error
    board_lines = ['wK . .', '. bK']
    rows, error = validate_board(board_lines)
    assert error == 'ROW_WIDTH_MISMATCH'
    assert rows is None

def test_validate_board_empty_board():
    # Verifies that an empty board input returns no rows and no error without crashing
    rows, error = validate_board([])
    assert rows is None
    assert error is None
