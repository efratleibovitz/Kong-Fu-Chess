from dataclasses import dataclass
from typing import Optional

from core.Entities import PieceType
from core.Entities.position import Position

@dataclass
class Piece:
    piece_id: str
    piece_type: PieceType
    is_white: bool
    position: Position
    cooldown_duration: float  # זמן בשיניות/מילישניות בין תנועות
    last_move_timestamp: float = 0.0