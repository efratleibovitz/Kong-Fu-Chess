# rules/collision_rules.py
from enum import Enum
from model.position import Position
from model.board import Board


class StepResult(Enum):
    CLEAR = "clear"
    CAPTURE = "capture"
    BLOCKED = "blocked"


class CollisionRules:
    @staticmethod
    def check_step(pos: Position, token: str, board: Board) -> StepResult:
        """Check what happens when `token` tries to step onto `pos`."""
        occupant = board.get_token(pos)
        if occupant == '.':
            return StepResult.CLEAR
        if occupant[0] != token[0]:
            return StepResult.CAPTURE
        return StepResult.BLOCKED
