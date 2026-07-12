#git repository:
#https://github.com/efratleibovitz/Kong-Fu-Chess.git

import sys
from iofiles.board_parser import parse_input, validate_board
from model.board import Board
from model.game_state import GameState
from engine.game_engine import GameEngine

def main():
    lines = sys.stdin.readlines()
    board_lines, command_lines = parse_input(lines)
    rows, error = validate_board(board_lines)

    if error:
        print(f'ERROR {error}')
        return

    if rows is None:
        return

    engine = GameEngine(GameState(Board(rows)))

    for cmd in command_lines:
        cmd = cmd.strip()
        if cmd == 'print board':
            engine.print_board()
        elif cmd.startswith('click '):
            _, x, y = cmd.split()
            engine.click(int(x), int(y))
        elif cmd.startswith('jump '):
            _, x, y = cmd.split()
            engine.jump(int(x), int(y))
        elif cmd.startswith('wait '):
            _, ms = cmd.split()
            engine.wait(int(ms))

main()
