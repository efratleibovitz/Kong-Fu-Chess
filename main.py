import sys
from infrastructure.board_parser import parse_input, validate_board
from core.Entities.board import Board
from core.game_service import GameService

def main():
    lines = sys.stdin.readlines()
    board_lines, command_lines = parse_input(lines)
    rows, error = validate_board(board_lines)

    if error:
        print(f'ERROR {error}')
        return

    if rows is None:
        return

    game = GameService(Board(rows))

    for cmd in command_lines:
        cmd = cmd.strip()
        if cmd == 'print board':
            game.print_board()
        elif cmd.startswith('click '):
            _, x, y = cmd.split()
            game.click(int(x), int(y))
        elif cmd.startswith('wait '):
            _, ms = cmd.split()
            game.wait(int(ms))

main()
