import sys
import re
from dataclasses import dataclass

VALID_TOKEN = re.compile(r'^[wb][KQRBNP]$|^\.$')
CELL_SIZE = 100

@dataclass
class Position:
    x: int
    y: int

class Board:
    def __init__(self, rows):
        self.rows = rows
        self.num_rows = len(rows)
        self.num_cols = len(rows[0]) if rows else 0

    def pixel_to_cell(self, x, y):
        col, row = x // CELL_SIZE, y // CELL_SIZE
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            return Position(col, row)
        return None

    def get_token(self, pos):
        return self.rows[pos.y][pos.x]

    def set_token(self, pos, token):
        self.rows[pos.y][pos.x] = token

    def print(self):
        for row in self.rows:
            print(' '.join(row))

def _sign(n):
    return (n > 0) - (n < 0)

def _is_blocked(from_pos, to_pos, board):
    step_x = _sign(to_pos.x - from_pos.x)
    step_y = _sign(to_pos.y - from_pos.y)
    x, y = from_pos.x + step_x, from_pos.y + step_y
    while (x, y) != (to_pos.x, to_pos.y):
        if board.get_token(Position(x, y)) != '.':
            return True
        x += step_x
        y += step_y
    return False

def is_valid_move(token, from_pos, to_pos, board):
    dx = abs(to_pos.x - from_pos.x)
    dy = abs(to_pos.y - from_pos.y)
    piece = token[1]
    color = token[0]

    dest_token = board.get_token(to_pos)
    if dest_token != '.' and dest_token[0] == color:
        return False

    if piece == 'K':
        return max(dx, dy) == 1
    if piece == 'R':
        if not (dx == 0 or dy == 0):
            return False
        return not _is_blocked(from_pos, to_pos, board)
    if piece == 'B':
        if not (dx == dy and dx > 0):
            return False
        return not _is_blocked(from_pos, to_pos, board)
    if piece == 'Q':
        if not (dx == 0 or dy == 0 or dx == dy):
            return False
        return not _is_blocked(from_pos, to_pos, board)
    if piece == 'N':
        return sorted([dx, dy]) == [1, 2]
    if piece == 'P':
        forward = -1 if color == 'w' else 1
        start_row = board.num_rows - 1 if color == 'w' else 0
        dy_signed = to_pos.y - from_pos.y
        if dy_signed == forward and dx == 0:
            return dest_token == '.'
        if dy_signed == forward * 2 and dx == 0:
            if from_pos.y != start_row:
                return False
            mid = Position(from_pos.x, from_pos.y + forward)
            return dest_token == '.' and board.get_token(mid) == '.'
        if dy_signed == forward and dx == 1:
            return dest_token != '.' and dest_token[0] != color
        return False
    return False

class GameService:
    def __init__(self, board):
        self.board = board
        self.selected = None
        self.clock = 0
        self.pending_moves = []
        self.pending_jumps = []
        self.game_over = False

    def _columns_of_move(self, from_pos, to_pos):
        return set(range(min(from_pos.x, to_pos.x), max(from_pos.x, to_pos.x) + 1))

    def _has_column_conflict(self, from_pos, to_pos):
        new_cols = self._columns_of_move(from_pos, to_pos)
        for _, pf, pt, _ in self.pending_moves:
            if new_cols & self._columns_of_move(pf, pt):
                return True
        return False

    def _is_in_transit(self, pos):
        return any(m[1] == pos for m in self.pending_moves)

    def _is_airborne(self, pos):
        return any(j[1] == pos for j in self.pending_jumps)

    def jump(self, x, y):
        if self.game_over:
            return
        pos = self.board.pixel_to_cell(x, y)
        if pos is None:
            return
        token = self.board.get_token(pos)
        if token == '.' or self._is_in_transit(pos) or self._is_airborne(pos):
            return
        self.pending_jumps.append((token, pos, self.clock + 1000))

    def click(self, x, y):
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

    def _schedule_move(self, from_pos, to_pos):
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

    def wait(self, ms):
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

def parse_input(lines):
    board_lines, command_lines = [], []
    section = None
    for line in lines:
        stripped = line.strip()
        if stripped == 'Board:':
            section = 'board'
        elif stripped == 'Commands:':
            section = 'commands'
        elif section == 'board':
            board_lines.append(stripped)
        elif section == 'commands':
            command_lines.append(stripped)
    return board_lines, command_lines

def validate_board(board_lines):
    rows = [line.split() for line in board_lines if line.strip()]
    if not rows:
        return None, None
    width = len(rows[0])
    for row in rows:
        if len(row) != width:
            return None, 'ROW_WIDTH_MISMATCH'
        for token in row:
            if not VALID_TOKEN.match(token):
                return None, 'UNKNOWN_TOKEN'
    return rows, None

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
        elif cmd.startswith('jump '):
            _, x, y = cmd.split()
            game.jump(int(x), int(y))
        elif cmd.startswith('wait '):
            _, ms = cmd.split()
            game.wait(int(ms))

main()
