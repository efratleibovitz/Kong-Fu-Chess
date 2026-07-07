import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import importlib
from io import StringIO
from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService

def test_white_pawn_promotes_to_queen_on_arrival():
    # Verifies that a white pawn reaching row 0 is replaced by a white queen
    game = GameService(Board([['.', '.'], ['.', 'wP']]))
    game.click(150, 150)
    game.click(150, 50)
    game.wait(1000)
    assert game.board.get_token(Position(1, 0)) == 'wQ'

def test_black_pawn_promotes_to_queen_on_arrival():
    # Verifies that a black pawn reaching the last row is replaced by a black queen
    game = GameService(Board([['.', 'bP'], ['.', '.']]))
    game.click(150, 50)
    game.click(150, 150)
    game.wait(1000)
    assert game.board.get_token(Position(1, 1)) == 'bQ'

def test_promoted_queen_can_move_diagonally(capsys, monkeypatch):
    # Verifies that after promotion the piece behaves as a queen and can move diagonally
    input_text = 'Board:\n. . .\n. wP .\n. . .\nCommands:\nclick 150 150\nclick 150 50\nwait 1000\nclick 150 50\nclick 250 150\nwait 1000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . .\n. . wQ\n. . .'

def test_white_pawn_double_step_arrives_correctly(capsys, monkeypatch):
    # Verifies that a white pawn double step from start row arrives at the correct cell
    input_text = 'Board:\n. . .\n. . .\n. . .\n. wP .\nCommands:\nclick 150 350\nclick 150 150\nwait 2000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . .\n. wP .\n. . .\n. . .'
