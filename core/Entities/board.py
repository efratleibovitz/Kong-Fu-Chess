from core.Entities.position import Position

CELL_SIZE = 100

class Board:
    def __init__(self, rows: list[list[str]]):
        self.rows = rows
        self.num_rows = len(rows)
        self.num_cols = len(rows[0]) if rows else 0

    def pixel_to_cell(self, x: int, y: int) -> Position | None:
        col, row = x // CELL_SIZE, y // CELL_SIZE
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            return Position(col, row)
        return None

    def get_token(self, pos: Position) -> str:
        return self.rows[pos.y][pos.x]

    def set_token(self, pos: Position, token: str):
        self.rows[pos.y][pos.x] = token

    def print(self):
        for row in self.rows:
            print(' '.join(row))
