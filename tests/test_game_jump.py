import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import importlib
from io import StringIO

def run(input_text, capsys, monkeypatch):
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    return capsys.readouterr().out.strip()

def test_jump_lands_same_square(capsys, monkeypatch):
    # piece jumps and lands back on same cell after 1000ms
    result = run("Board:\n. . .\n. wK .\n. . .\nCommands:\njump 150 150\nwait 1000\nprint board", capsys, monkeypatch)
    assert result == ". . .\n. wK .\n. . .", repr(result)

def test_airborne_piece_captures_arriving_enemy(capsys, monkeypatch):
    # wK jumps, bR moves toward wK cell, bR is destroyed on arrival
    result = run("Board:\n. . .\nwK . bR\n. . .\nCommands:\njump 50 150\nclick 250 150\nclick 50 150\nwait 1000\nprint board", capsys, monkeypatch)
    assert result == ". . .\nwK . .\n. . .", repr(result)

def test_jump_too_late_does_not_save_piece(capsys, monkeypatch):
    # bR moves first, wK tries to jump after bR already arrived
    result = run("Board:\n. . .\nwK . bR\n. . .\nCommands:\nclick 250 150\nclick 50 150\nwait 1000\njump 50 150\nprint board", capsys, monkeypatch)
    assert result == ". . .\nbR . .\n. . .", repr(result)

def test_enemy_arrives_after_landing_captures_normally(capsys, monkeypatch):
    # wK jumps and lands, then bR arrives and captures normally
    result = run("Board:\n. . . .\nwK . . bR\n. . . .\nCommands:\njump 50 150\nwait 1000\nclick 350 150\nclick 50 150\nwait 3000\nprint board", capsys, monkeypatch)
    assert result == ". . . .\nbR . . .\n. . . .", repr(result)

def test_cannot_jump_while_moving(capsys, monkeypatch):
    # wR is in transit, jump on its origin cell is ignored
    result = run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 500\njump 50 50\nwait 1500\nprint board", capsys, monkeypatch)
    assert result == ". . wR", repr(result)

def test_airborne_capture_only_enemy(capsys, monkeypatch):
    # wK jumps, friendly wR moves to wK cell — no capture
    result = run("Board:\n. . .\nwK . wR\n. . .\nCommands:\njump 50 150\nclick 250 150\nclick 50 150\nwait 1000\nprint board", capsys, monkeypatch)
    assert result == ". . .\nwK . wR\n. . .", repr(result)
