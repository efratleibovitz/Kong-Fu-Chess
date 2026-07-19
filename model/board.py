from typing import List, Optional

from model.position import Position


class Board:
    def __init__(self, rows: List[List]):
        # rows[row][col] — row 0 is the top of the board
        from model.piece import Piece
        converted = []
        for r, row in enumerate(rows):
            converted_row = []
            for c, cell in enumerate(row):
                if isinstance(cell, str) and cell != '.':
                    converted_row.append(Piece.from_token(cell, Position(c, r)))
                elif isinstance(cell, str):
                    converted_row.append(None)
                else:
                    converted_row.append(cell)  # already Piece or None
            converted.append(converted_row)
        self.rows = converted
        self.initial_rows = [[cell.token if cell else '.' for cell in row] for row in converted]
        self.num_rows = len(rows)
        self.num_cols = len(rows[0]) if rows else 0

    def is_within_bounds(self, pos: Position) -> bool:
        return 0 <= pos.row < self.num_rows and 0 <= pos.col < self.num_cols

    def get_piece(self, pos: Position):
        """Returns Piece or None."""
        return self.rows[pos.row][pos.col]

    def set_piece(self, pos: Position, piece):
        """Set a Piece or None at pos."""
        self.rows[pos.row][pos.col] = piece

    def get_token(self, pos: Position) -> str:
        cell = self.rows[pos.row][pos.col]
        return cell.token if cell else '.'

    def set_token(self, pos: Position, token: str):
        from model.piece import Piece
        self.rows[pos.row][pos.col] = Piece.from_token(token, pos) if token != '.' else None
