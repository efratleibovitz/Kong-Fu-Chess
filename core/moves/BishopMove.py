from core.moves.MovementStrategy import MovementStrategy
from core.moves.utils import is_blocked
from core.Entities.position import Position

class BishopMove(MovementStrategy):
    def is_valid(self, from_pos: Position, to_pos: Position, board) -> bool:
        dx = abs(to_pos.x - from_pos.x)
        dy = abs(to_pos.y - from_pos.y)
        if not (dx == dy and dx > 0):
            return False
        return not is_blocked(from_pos, to_pos, board)
