from core.Entities.board import Board
from core.Entities.position import Position
from core.movement_validator import is_valid_move

class GameService:
    def __init__(self, board: Board):
        self.board = board
        self.selected: Position | None = None
        self.clock = 0
        self.pending_moves: list[tuple[str, Position, Position, int]] = []
        self.pending_jumps: list[tuple[str, Position, int]] = []
        self.game_over = False

    def _columns_of_move(self, from_pos: Position, to_pos: Position) -> set:
        min_col = min(from_pos.x, to_pos.x)
        max_col = max(from_pos.x, to_pos.x)
        return set(range(min_col, max_col + 1))

    def _has_column_conflict(self, from_pos: Position, to_pos: Position) -> bool:
        new_cols = self._columns_of_move(from_pos, to_pos)
        for _, pf, pt, _ in self.pending_moves:
            if new_cols & self._columns_of_move(pf, pt):
                return True
        return False

    def _is_in_transit(self, pos: Position) -> bool:
        return any(m[1] == pos for m in self.pending_moves)

    def _is_airborne(self, pos: Position) -> bool:
        return any(j[1] == pos for j in self.pending_jumps)

    def jump(self, x: int, y: int):
        if self.game_over:
            return
        pos = self.board.pixel_to_cell(x, y)
        if pos is None:
            return
        token = self.board.get_token(pos)
        if token == '.' or self._is_in_transit(pos) or self._is_airborne(pos):
            return
        self.pending_jumps.append((token, pos, self.clock + 1000))

    def click(self, x: int, y: int):
        if self.game_over:
            return
        pos = self.board.pixel_to_cell(x, y)
        if pos is None:
            return

        dest_token = self.board.get_token(pos)

        if dest_token != '.' and (self.selected is None or dest_token[0] == self.board.get_token(self.selected)[0]):
            if not self._is_in_transit(pos):
                self.selected = pos
        elif self.selected is not None:
            token = self.board.get_token(self.selected)
            if is_valid_move(token, self.selected, pos, self.board):
                if not self._has_column_conflict(self.selected, pos):
                    self._schedule_move(self.selected, pos)
                    self.selected = None

    def _schedule_move(self, from_pos: Position, to_pos: Position):
        token = self.board.get_token(from_pos)
        distance = max(abs(to_pos.x - from_pos.x), abs(to_pos.y - from_pos.y))
        arrive_time = self.clock + distance * 500
        intercepted = any(
            j[1] == to_pos and j[0][0] != token[0]
            for j in self.pending_jumps
        )
        if intercepted:
            self.board.set_token(from_pos, '.')
        else:
            self.pending_moves.append((token, from_pos, to_pos, arrive_time))

    def wait(self, ms: int):
        if self.game_over:
            return
        self.clock += ms
        settled = [m for m in self.pending_moves if m[3] <= self.clock]
        for token, from_pos, to_pos, _ in settled:
            captured = self.board.get_token(to_pos)
            self.board.set_token(from_pos, '.')
            self.board.set_token(to_pos, token)
            if captured != '.' and captured[1] == 'K':
                self.game_over = True
            if token[1] == 'P':
                promote_row = 0 if token[0] == 'w' else self.board.num_rows - 1
                if to_pos.y == promote_row:
                    self.board.set_token(to_pos, token[0] + 'Q')
        self.pending_moves = [m for m in self.pending_moves if m[3] > self.clock]
        self.pending_jumps = [j for j in self.pending_jumps if j[2] > self.clock]

    def print_board(self):
        self.board.print()
