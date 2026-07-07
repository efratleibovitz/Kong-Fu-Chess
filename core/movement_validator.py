from core.Entities.position import Position

def is_valid_move(token: str, from_pos: Position, to_pos: Position, board) -> bool:
    dx = abs(to_pos.x - from_pos.x)
    dy = abs(to_pos.y - from_pos.y)
    piece = token[1]
    color = token[0]

    # Cannot capture own piece
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

def _is_blocked(from_pos: Position, to_pos: Position, board) -> bool:
    step_x = _sign(to_pos.x - from_pos.x)
    step_y = _sign(to_pos.y - from_pos.y)
    x, y = from_pos.x + step_x, from_pos.y + step_y
    while (x, y) != (to_pos.x, to_pos.y):
        if board.get_token(Position(x, y)) != '.':
            return True
        x += step_x
        y += step_y
    return False

def _sign(n: int) -> int:
    return (n > 0) - (n < 0)
