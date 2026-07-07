import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import importlib
from io import StringIO
from core.Entities.board import Board
from core.Entities.position import Position
from core.game_service import GameService

def test_king_capture_sets_game_over():
    # Verifies that capturing an enemy king sets the game_over flag to True
    game = GameService(Board([['wR', '.', 'bK']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    assert game.game_over is True

def test_king_capture_ends_game(capsys, monkeypatch):
    # Verifies that capturing the enemy king results in the correct final board state
    input_text = 'Board:\nwR . bK\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . wR'

def test_no_moves_after_game_over(capsys, monkeypatch):
    # Verifies that after a king is captured, further move commands are ignored
    input_text = 'Board:\nwR . bK\nbR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nclick 50 150\nclick 150 150\nwait 1000\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == '. . wR\nbR . .'

def test_click_ignored_after_game_over():
    # Verifies that clicking a piece after game over does not select it
    game = GameService(Board([['wR', '.', 'bK']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    game.click(50, 50)
    assert game.selected is None

def test_wait_ignored_after_game_over():
    # Verifies that calling wait after game over does not change the board state
    game = GameService(Board([['wR', '.', 'bK'], ['bR', '.', '.']]))
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    game.click(50, 150)
    game.click(150, 150)
    game.wait(1000)
    assert game.board.get_token(Position(0, 1)) == 'bR'
    assert game.board.get_token(Position(1, 1)) == '.'
