from dataclasses import dataclass
from enum import Enum
from model.position import Position


class PieceColor(Enum):
    WHITE = "white"
    BLACK = "black"


class PieceKind(Enum):
    KING   = "K"
    QUEEN  = "Q"
    ROOK   = "R"
    BISHOP = "B"
    KNIGHT = "N"
    PAWN   = "P"


class PieceState(Enum):
    IDLE     = "idle"
    MOVING   = "moving"
    AIRBORNE = "airborne"
    CAPTURED = "captured"


@dataclass
class Piece:
    piece_id: str          # e.g. "wK", "bR1"
    color: PieceColor
    kind: PieceKind
    cell: Position
    state: PieceState = PieceState.IDLE

    @property
    def token(self) -> str:
        """String token used by Board cells, e.g. 'wK', 'bR'."""
        prefix = 'w' if self.color == PieceColor.WHITE else 'b'
        return prefix + self.kind.value

    @staticmethod
    def from_token(token: str, cell: Position, piece_id: str | None = None) -> "Piece":
        """Create a Piece from a board token string like 'wK' or 'bR'."""
        color = PieceColor.WHITE if token[0] == 'w' else PieceColor.BLACK
        kind  = PieceKind(token[1])
        pid   = piece_id if piece_id else token
        return Piece(piece_id=pid, color=color, kind=kind, cell=cell)
