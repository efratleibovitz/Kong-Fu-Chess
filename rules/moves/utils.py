from model.position import Position

def _sign(n):
    return (n > 0) - (n < 0)

def is_blocked(from_pos: Position, to_pos: Position, board) -> bool:
    step_x = _sign(to_pos.x - from_pos.x)
    step_y = _sign(to_pos.y - from_pos.y)
    x, y = from_pos.x + step_x, from_pos.y + step_y
    while (x, y) != (to_pos.x, to_pos.y):
        if board.get_token(Position(x, y)) != '.':
            return True
        x += step_x
        y += step_y
    return False
