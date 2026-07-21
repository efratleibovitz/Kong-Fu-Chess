#git repository:
#https://github.com/efratleibovitz/Kong-Fu-Chess.git

import argparse
import sys


def _run_text_mode():
    from iofiles.board_parser import parse_input, validate_board
    from model.board import Board
    from model.game_state import GameState
    from engine.game_engine import GameEngine

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


def main():
    parser = argparse.ArgumentParser(description="Kong Fu Chess")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", help="play solo with the graphical UI")
    mode.add_argument("--online", action="store_true", help="play online (matchmaking + server)")
    mode.add_argument("--server", action="store_true", help="start the game server")
    args = parser.parse_args()

    if args.server:
        import asyncio
        from server.app import main as server_main
        asyncio.run(server_main())
    elif args.online:
        from main_network import main as network_main
        network_main()
    elif args.gui:
        from main_ui import main as ui_main
        ui_main()
    else:
        _run_text_mode()


if __name__ == '__main__':
    main()
