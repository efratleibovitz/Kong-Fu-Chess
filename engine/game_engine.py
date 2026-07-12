# engine/game_engine.py
from model.game_state import GameState
from model.position import Position
from model.board import Board
from input.board_mapper import BoardMapper
from rules.rule_engine import RuleEngine
from iofiles.board_printer import print_board as _print_board


class GameEngine:
    def __init__(self, state: GameState):
        self.state = state
        self.rule_engine = RuleEngine()

    # --- helpers ---

    def _columns_of_move(self, from_pos: Position, to_pos: Position) -> set:
        min_col = min(from_pos.x, to_pos.x)
        max_col = max(from_pos.x, to_pos.x)
        return set(range(min_col, max_col + 1))

    def _has_column_conflict(self, from_pos: Position, to_pos: Position) -> bool:
        new_cols = self._columns_of_move(from_pos, to_pos)
        for _, pf, pt, _ in self.state.pending_moves:
            if new_cols & self._columns_of_move(pf, pt):
                return True
        return False

    def _is_in_transit(self, pos: Position) -> bool:
        return any(m[1] == pos for m in self.state.pending_moves)

    def _is_airborne(self, pos: Position) -> bool:
        return any(j[1] == pos for j in self.state.pending_jumps)

    def _pixel_to_cell(self, x: int, y: int) -> Position | None:
        if not BoardMapper.is_within_bounds(x, y, self.state.board.num_cols, self.state.board.num_rows):
            return None
        return BoardMapper.pixel_to_cell(x, y)

    # --- public interface ---

    def click(self, x: int, y: int):
        if self.state.game_over:
            return
        pos = self._pixel_to_cell(x, y)
        if pos is None:
            return

        board = self.state.board
        dest_token = board.get_token(pos)
        selected = self.state.selected_position

        if dest_token != '.' and (selected is None or dest_token[0] == board.get_token(selected)[0]):
            if not self._is_in_transit(pos):
                self.state.selected_position = pos
        elif selected is not None:
            validation = self.rule_engine.validate_move(board, selected, pos)
            if validation["is_valid"]:
                if not self._has_column_conflict(selected, pos):
                    self._schedule_move(selected, pos)
                    self.state.selected_position = None

    def jump(self, x: int, y: int):
        if self.state.game_over:
            return
        pos = self._pixel_to_cell(x, y)
        if pos is None:
            return
        token = self.state.board.get_token(pos)
        if token == '.' or self._is_in_transit(pos) or self._is_airborne(pos):
            return
        self.state.pending_jumps.append((token, pos, self.state.clock + 1000))

    def _schedule_move(self, from_pos: Position, to_pos: Position):
        board = self.state.board
        token = board.get_token(from_pos)
        distance = max(abs(to_pos.x - from_pos.x), abs(to_pos.y - from_pos.y))
        arrive_time = self.state.clock + distance * 500
        intercepted = any(
            j[1] == to_pos and j[0][0] != token[0]
            for j in self.state.pending_jumps
        )
        if intercepted:
            board.set_token(from_pos, '.')
        else:
            self.state.pending_moves.append((token, from_pos, to_pos, arrive_time))

    def wait(self, ms: int):
        if self.state.game_over:
            return
        self.state.clock += ms
        board = self.state.board
        settled = [m for m in self.state.pending_moves if m[3] <= self.state.clock]
        for token, from_pos, to_pos, _ in settled:
            captured = board.get_token(to_pos)
            board.set_token(from_pos, '.')
            board.set_token(to_pos, token)
            if captured != '.' and captured[1] == 'K':
                self.state.game_over = True
            if token[1] == 'P':
                promote_row = 0 if token[0] == 'w' else board.num_rows - 1
                if to_pos.y == promote_row:
                    board.set_token(to_pos, token[0] + 'Q')
        self.state.pending_moves = [m for m in self.state.pending_moves if m[3] > self.state.clock]
        self.state.pending_jumps = [j for j in self.state.pending_jumps if j[2] > self.state.clock]

    def print_board(self):
        _print_board(self.state.board)

    # convenience properties so tests can access state directly
    @property
    def board(self) -> Board:
        return self.state.board

    @property
    def selected(self) -> Position | None:
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
