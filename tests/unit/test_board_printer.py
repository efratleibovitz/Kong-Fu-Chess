import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from model.board import Board
from iofiles.board_printer import print_board


def test_print_board_output(capsys):
    # Verifies that print_board() outputs each row as space-separated tokens
    board = Board([['wK', '.'], ['.', 'bK']])
    print_board(board)
    captured = capsys.readouterr()
    assert captured.out == 'wK .\n. bK\n'
