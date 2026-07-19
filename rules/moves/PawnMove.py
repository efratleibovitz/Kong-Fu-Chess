from rules.moves.MovementStrategy import MovementStrategy
from model.position import Position
from model.piece import PieceColor


class PawnMove(MovementStrategy):
    def is_valid(self, from_pos: Position, to_pos: Position, board) -> bool:
        piece = board.get_piece(from_pos)
        is_white = piece.color == PieceColor.WHITE
        forward = -1 if is_white else 1
        start_row = board.num_rows - 2 if is_white else 1
        dcol = abs(to_pos.col - from_pos.col)
        drow_signed = to_pos.row - from_pos.row

        dest = board.get_piece(to_pos)

        # one step forward
        if drow_signed == forward and dcol == 0:
            return dest is None
        # two steps forward from start row
        if drow_signed == forward * 2 and dcol == 0:
            if from_pos.row != start_row:
                return False
            mid = Position(from_pos.col, from_pos.row + forward)
            return dest is None and board.get_piece(mid) is None
        # diagonal capture
        if drow_signed == forward and dcol == 1:
            return dest is not None and dest.color != piece.color
        return False
