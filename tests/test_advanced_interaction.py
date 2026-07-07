import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import importlib
from io import StringIO
from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService

def test_enemy_collision_white_started_first(capsys, monkeypatch):
    # Verifies that when two enemies move toward each other, the one who moved first wins and arrives
    input_text = 'Board:\nwR . . bR\nCommands:\nclick 50 50\nclick 350 50\nclick 350 50\nclick 50 50\nwait 3000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . . wR'

def test_enemy_collision_black_started_first(capsys, monkeypatch):
    # Verifies that when black moves first toward white, black wins and arrives at white's position
    input_text = 'Board:\nwR . . bR\nCommands:\nclick 350 50\nclick 50 50\nclick 50 50\nclick 350 50\nwait 3000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == 'bR . . .'

def test_cannot_start_move_through_friendly_piece(capsys, monkeypatch):
    # Verifies that a rook cannot move through a friendly piece blocking its path
    input_text = 'Board:\n. . .\nwR wP .\n. . .\nCommands:\nclick 50 150\nclick 250 150\nwait 2000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . .\nwR wP .\n. . .'

def test_dynamic_block_tactic_not_in_common_route(capsys, monkeypatch):
    # Verifies that a piece moving through a column blocks another piece from entering that column
    input_text = 'Board:\n. . . .\nwQ . . bK\n. . bP .\n. . . .\nCommands:\nclick 50 150\nclick 350 150\nwait 200\nclick 250 250\nclick 250 150\nwait 3000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . . .\n. . . wQ\n. . bP .\n. . . .'

def test_knight_cannot_land_on_friendly_piece(capsys, monkeypatch):
    # Verifies that a knight cannot land on a square occupied by a friendly piece
    input_text = 'Board:\n. wP .\n. . .\nwN . .\nCommands:\nclick 50 250\nclick 150 50\nwait 1000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. wP .\n. . .\nwN . .'

def test_premove_does_not_execute_in_common_route(capsys, monkeypatch):
    # Verifies that a premove through overlapping columns is blocked while a piece is in transit
    input_text = 'Board:\nwR . .\nCommands:\nclick 50 50\nclick 150 50\nclick 50 50\nclick 250 50\nwait 2000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. wR .'
