from rules.moves.MovementStrategy import MovementStrategy
from model.position import Position

class KingMove(MovementStrategy):
    def is_valid(self, from_pos: Position, to_pos: Position, board) -> bool:
        dx = abs(to_pos.x - from_pos.x)
        dy = abs(to_pos.y - from_pos.y)
        return max(dx, dy) == 1
