# rules/collision_rules.py
from enum import Enum
from core.model.position import Position
from core.model.board import Board


class StepResult(Enum):
    CLEAR = "clear"
    CAPTURE = "capture"
    BLOCKED = "blocked"


class CollisionRules:
    @staticmethod
    def check_step(pos: Position, piece, board: Board) -> StepResult:
        """Check what happens when `piece` tries to step onto `pos`."""
        from core.model.piece import Piece
        if isinstance(piece, str):
            piece = Piece.from_token(piece, pos)
        occupant = board.get_piece(pos)
        if occupant is None:
            return StepResult.CLEAR
        if occupant.color != piece.color:
            return StepResult.CAPTURE
        return StepResult.BLOCKED
