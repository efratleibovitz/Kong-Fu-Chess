from core.moves.MovementStrategy import MovementStrategy
from core.Entities.position import Position

class PawnMove(MovementStrategy):
    def is_valid(self, from_pos: Position, to_pos: Position, board) -> bool:
        token = board.get_token(from_pos)
        color = token[0]
        dest_token = board.get_token(to_pos)
        forward = -1 if color == 'w' else 1
        start_row = board.num_rows - 1 if color == 'w' else 0
        dx = abs(to_pos.x - from_pos.x)
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
