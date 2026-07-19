from model.position import Position


def _sign(n):
    return (n > 0) - (n < 0)


def is_blocked(from_pos: Position, to_pos: Position, board) -> bool:
    step_col = _sign(to_pos.col - from_pos.col)
    step_row = _sign(to_pos.row - from_pos.row)
    col, row = from_pos.col + step_col, from_pos.row + step_row
    while (col, row) != (to_pos.col, to_pos.row):
        if board.get_piece(Position(col, row)) is not None:
            return True
        col += step_col
        row += step_row
    return False
