from core.Entities.board import Board
from core.Entities.position import Position
from core.movement_validator import is_valid_move

class GameService:
    def __init__(self, board: Board):
        self.board = board
        self.selected: Position | None = None
        self.clock = 0
        # pending_moves: list of (from_token, from_pos, to_pos, arrive_time)
        self.pending_moves: list[tuple[str, Position, Position, int]] = []

    def _is_in_transit(self, pos: Position) -> bool:
        return any(m[1] == pos for m in self.pending_moves)

    def click(self, x: int, y: int):
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
                self._schedule_move(self.selected, pos)
                self.selected = None

    def _schedule_move(self, from_pos: Position, to_pos: Position):
        token = self.board.get_token(from_pos)
        distance = max(abs(to_pos.x - from_pos.x), abs(to_pos.y - from_pos.y))
        arrive_time = self.clock + distance * 1000
        self.pending_moves.append((token, from_pos, to_pos, arrive_time))

    def wait(self, ms: int):
        self.clock += ms
        settled = [m for m in self.pending_moves if m[3] <= self.clock]
        for token, from_pos, to_pos, _ in settled:
            self.board.set_token(from_pos, '.')
            self.board.set_token(to_pos, token)
        self.pending_moves = [m for m in self.pending_moves if m[3] > self.clock]

    def print_board(self):
        self.board.print()
