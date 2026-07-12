# infrastructure/input/board_mapper.py
from model.position import Position

class BoardMapper:
    CELL_SIZE = 100

    @staticmethod
    def pixel_to_cell(x: int, y: int) -> Position:
        col = x // BoardMapper.CELL_SIZE
        row = y // BoardMapper.CELL_SIZE
        return Position(col, row)

    @staticmethod
    def is_within_bounds(x: int, y: int, num_cols: int, num_rows: int) -> bool:
        """
        בודקת האם קליק בפיקסלים נמצא בתוך גבולות הלוח.
        """
        col = x // BoardMapper.CELL_SIZE
        row = y // BoardMapper.CELL_SIZE
        return 0 <= col < num_cols and 0 <= row < num_rows