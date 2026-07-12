from model.position import Position

class Board:
    def __init__(self, rows: list[list[str]]):
        self.rows = rows
        self.num_rows = len(rows)
        self.num_cols = len(rows[0]) if rows else 0

    def is_within_bounds(self, pos: Position) -> bool:
        """בודק האם המיקום הלוגי נמצא בתוך הלוח"""
        return 0 <= pos.y < self.num_rows and 0 <= pos.x < self.num_cols

    def get_token(self, pos: Position) -> str:
        return self.rows[pos.y][pos.x]

    def set_token(self, pos: Position, token: str):
        self.rows[pos.y][pos.x] = token

    def print(self):
        for row in self.rows:
            print(' '.join(row))
