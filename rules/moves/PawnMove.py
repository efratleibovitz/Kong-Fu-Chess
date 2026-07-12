from rules.moves.MovementStrategy import MovementStrategy
from model.position import Position


class PawnMove(MovementStrategy):
    def is_valid(self, from_pos: Position, to_pos: Position, board) -> bool:
        token = board.get_token(from_pos)
        color = token[0]
        dest_token = board.get_token(to_pos)
        forward = -1 if color == 'w' else 1
        start_row = board.num_rows - 1 if color == 'w' else 0
        dcol = abs(to_pos.col - from_pos.col)
        drow_signed = to_pos.row - from_pos.row

        # one step forward
        if drow_signed == forward and dcol == 0:
            return dest_token == '.'
        # two steps forward from start row
        if drow_signed == forward * 2 and dcol == 0:
            if from_pos.row != start_row:
                return False
            mid = Position(from_pos.col, from_pos.row + forward)
            return dest_token == '.' and board.get_token(mid) == '.'
        # diagonal capture
        if drow_signed == forward and dcol == 1:
            return dest_token != '.' and dest_token[0] != color
        return False
