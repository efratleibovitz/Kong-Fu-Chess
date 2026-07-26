from core.iofiles.board_parser import parse_input, validate_board
from core.model.board import Board
from core.model.default_board import DEFAULT_BOARD
from core.model.game_state import GameState
from core.engine.game_engine import GameEngine
from view.screen import Screen

def main():
    state = GameState(Board(DEFAULT_BOARD))
    state.player_names = {'w': 'White', 'b': 'Black'}
    engine = GameEngine(state)
    Screen(engine, state).run()

if __name__ == '__main__':
    main()
