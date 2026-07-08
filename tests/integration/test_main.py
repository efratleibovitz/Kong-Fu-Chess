import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def test_main_select_and_move():
    from core.Entities.board import Board
    from core.Entities.position import Position
    from core.game_service import GameService

    game = GameService(Board([['wK', '.', '.'], ['.', '.', '.'], ['.', '.', '.']]))
    game.click(50, 50)
    game.click(150, 150)
    game.wait(1000)
    assert game.board.get_token(Position(1, 1)) == 'wK'
    assert game.board.get_token(Position(0, 0)) == '.'


def test_main_error_unknown_token(capsys, monkeypatch):
    from io import StringIO
    import importlib

    input_text = 'Board:\nwK xZ\n. .\nCommands:\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == 'ERROR UNKNOWN_TOKEN'


def test_main_error_row_width_mismatch(capsys, monkeypatch):
    from io import StringIO
    import importlib

    input_text = 'Board:\nwK . .\n. bK\nCommands:\nprint board\n'
    monkeypatch.setattr('sys.stdin', StringIO(input_text))
    import main
    importlib.reload(main)
    captured = capsys.readouterr()
    assert captured.out.strip() == 'ERROR ROW_WIDTH_MISMATCH'
