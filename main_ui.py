from core.iofiles.board_parser import parse_input, validate_board
from core.model.board import Board
from core.model.game_state import GameState
from core.engine.game_engine import GameEngine
from view.screen import Screen

DEFAULT_BOARD = [
    ['bR', 'bN', 'bB', 'bK', 'bQ', 'bB', 'bN', 'bR'],
    ['bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP'],
    ['wR', 'wN', 'wB', 'wK', 'wQ', 'wB', 'wN', 'wR'],
]

def main():
    state = GameState(Board(DEFAULT_BOARD))
    state.player_names = {'w': 'White', 'b': 'Black'}
    engine = GameEngine(state)
    Screen(engine, state).run()

if __name__ == '__main__':
    main()
