import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from engine.game_engine import GameEngine
from iofiles.board_parser import parse_input, validate_board
from model.board import Board
from model.game_state import GameState


def _run_case(input_text: str) -> str:
    lines = input_text.splitlines()
    board_lines, command_lines = parse_input(lines)
    rows, error = validate_board(board_lines)
    if error:
        return f"ERROR {error}"

    engine = GameEngine(GameState(Board(rows)))
    output = []
    for cmd in command_lines:
        cmd = cmd.strip()
        if cmd == 'print board':
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                engine.print_board()
            output.append(buffer.getvalue().strip())
        elif cmd.startswith('click '):
            _, x, y = cmd.split()
            engine.click(int(x), int(y))
        elif cmd.startswith('jump '):
            _, x, y = cmd.split()
            engine.jump(int(x), int(y))
        elif cmd.startswith('wait '):
            _, ms = cmd.split()
            engine.wait(int(ms))

    return '\n'.join(output)


def test_parse_empty_board_3x3():
    input_text = "Board:\n. . .\n. . .\n. . .\nCommands:\nprint board\n"
    assert _run_case(input_text) == ". . .\n. . .\n. . ."


def test_parse_rectangular_board_3x4():
    input_text = "Board:\nwK . . bK\n. . . .\nwR . . bR\nCommands:\nprint board\n"
    assert _run_case(input_text) == "wK . . bK\n. . . .\nwR . . bR"


def test_reject_unknown_token():
    input_text = "Board:\nwK xZ\n. .\nCommands:\nprint board\n"
    assert _run_case(input_text) == "ERROR UNKNOWN_TOKEN"


def test_reject_row_width_mismatch():
    input_text = "Board:\nwK . .\n. bK\nCommands:\nprint board\n"
    assert _run_case(input_text) == "ERROR ROW_WIDTH_MISMATCH"


def test_select_piece_and_move():
    input_text = "Board:\nwK . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 150 150\nwait 1000\nprint board\n"
    assert _run_case(input_text) == ". . .\n. wK .\n. . ."


def test_rook_straight_move():
    input_text = "Board:\nwR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board\n"
    assert _run_case(input_text) == ". . wR"


def test_white_pawn_double_from_start_valid():
    input_text = "Board:\n. . .\n. . .\n. . .\n. wP .\nCommands:\nclick 150 350\nclick 150 150\nwait 2000\nprint board\n"
    assert _run_case(input_text) == ". . .\n. wP .\n. . .\n. . ."


def test_jump_lands_same_square():
    input_text = "Board:\n. . .\n. wK .\n. . .\nCommands:\njump 150 150\nwait 1000\nprint board\n"
    assert _run_case(input_text) == ". . .\n. wK .\n. . ."
