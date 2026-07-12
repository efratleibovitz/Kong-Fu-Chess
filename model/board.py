from typing import List

from model.position import Position


class Board:
    def __init__(self, rows: List[List[str]]):
        # rows[row][col] — row 0 is the top of the board
        self.rows = rows
        self.num_rows = len(rows)
        self.num_cols = len(rows[0]) if rows else 0

    def is_within_bounds(self, pos: Position) -> bool:
        return 0 <= pos.row < self.num_rows and 0 <= pos.col < self.num_cols

    def get_token(self, pos: Position) -> str:
        return self.rows[pos.row][pos.col]

    def set_token(self, pos: Position, token: str):
        self.rows[pos.row][pos.col] = token
