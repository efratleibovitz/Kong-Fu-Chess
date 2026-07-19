# engine/game_engine.py
from typing import Optional

from model.game_state import GameState
from model.position import Position
from model.board import Board
from input.board_mapper import BoardMapper
from rules.rule_engine import RuleEngine
from engine.move_scheduler import MoveScheduler
from realtime.move_settler import MoveSettler
from iofiles.board_printer import print_board as _print_board


class GameEngine:
    def __init__(self, state: GameState):
        self.state = state
        self.rule_engine = RuleEngine()

    # --- helpers ---

    def _pixel_to_cell(self, x: int, y: int) -> Optional[Position]:
        if not BoardMapper.is_within_bounds(x, y, self.state.board.num_cols, self.state.board.num_rows):
            return None
        return BoardMapper.pixel_to_cell(x, y)

    def _is_in_transit(self, pos: Position) -> bool:
        return any(m[1] == pos for m in self.state.pending_moves)

    def _is_airborne(self, pos: Position) -> bool:
        return any(j[1] == pos for j in self.state.pending_jumps)

    def _is_in_cooldown(self, pos: Position) -> bool:
        key = (pos.col, pos.row)
        expire = self.state.cooldowns.get(key)
        return expire is not None and expire > self.state.clock

    # --- public interface ---

    def click(self, x: int, y: int):
        if self.state.game_over:
            return
        pos = self._pixel_to_cell(x, y)
        if pos is None:
            return

        board = self.state.board
        dest_piece = board.get_piece(pos)
        selected = self.state.selected_position

        if dest_piece is not None and (selected is None or dest_piece.color == board.get_piece(selected).color):
            if not self._is_in_transit(pos) and not self._is_in_cooldown(pos):
                self.state.selected_position = pos
                self.state.events.emit('selection_changed')
        elif selected is not None:
            validation = self.rule_engine.validate_move(board, selected, pos)
            if validation["is_valid"]:
                if not MoveScheduler.has_column_conflict(selected, pos, self.state):
                    MoveScheduler.schedule(selected, pos, self.state)
                    self.state.selected_position = None
                    self.state.events.emit('selection_changed')

    def jump(self, x: int, y: int):
        if self.state.game_over:
            return
        pos = self._pixel_to_cell(x, y)
        if pos is None:
            return
        piece = self.state.board.get_piece(pos)
        if piece is None or self._is_in_transit(pos) or self._is_airborne(pos):
            return
        self.state.pending_jumps.append((piece, pos, self.state.clock + 1000))

    def wait(self, ms: int):
        if self.state.game_over:
            return
        MoveSettler.settle(self.state, ms)

    def restart(self):
        from model.board import Board
        fresh = GameState(Board([row[:] for row in self.state.board.initial_rows]))
        fresh.player_names = dict(self.state.player_names)
        bus = self.state.events
        self.state.__dict__.update(fresh.__dict__)
        self.state.events = bus
        self.state.events.emit('restarted')

    def print_board(self):
        _print_board(self.state.board)

    # --- convenience properties for tests ---

    @property
    def board(self) -> Board:
        return self.state.board

    @property
    def selected(self) -> Optional[Position]:
        return self.state.selected_position

    @property
    def pending_moves(self) -> list:
        return self.state.pending_moves

    @property
    def pending_jumps(self) -> list:
        return self.state.pending_jumps

    @property
    def game_over(self) -> bool:
        return self.state.game_over
