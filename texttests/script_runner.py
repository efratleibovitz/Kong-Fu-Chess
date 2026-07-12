from iofiles.board_parser import parse_input, validate_board
from model.board import Board
from model.game_state import GameState
from engine.game_engine import GameEngine
from texttests.script_parser import ScriptParser
import io
import sys

def run_script(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    board_lines, commands = parse_input(lines)
    rows, _ = validate_board(board_lines)
    engine = GameEngine(GameState(Board(rows)))
    parser = ScriptParser(engine)

    # הרצת פקודות
    for cmd in commands:
        if cmd.strip() == "print board":
            # לכידת הפלט של ההדפסה לצורך השוואה
            old_stdout = sys.stdout
            sys.stdout = mystdout = io.StringIO()
            engine.print_board()
            sys.stdout = old_stdout
            
            print(f"Captured output:\n{mystdout.getvalue()}")
        else:
            parser.execute_command(cmd)

# ניתן להריץ את זה דרך שורת הפקודה
if __name__ == "__main__":
    run_script(sys.argv[1])