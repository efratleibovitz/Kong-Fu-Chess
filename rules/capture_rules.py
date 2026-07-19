# rules/capture_rules.py
from model.board import Board
from model.position import Position
from model.piece import Piece, PieceKind, PieceColor


class CaptureRules:

    @staticmethod
    def is_king_captured(piece: Piece) -> bool:
        return piece is not None and piece.kind == PieceKind.KING

    @staticmethod
    def should_promote(piece: Piece, to_pos: Position, board: Board) -> bool:
        if piece.kind != PieceKind.PAWN:
            return False
        promote_row = 0 if piece.color == PieceColor.WHITE else board.num_rows - 1
        return to_pos.row == promote_row

    @staticmethod
    def promote(piece: Piece) -> Piece:
        from model.position import Position
        return Piece(piece_id=piece.piece_id, color=piece.color, kind=PieceKind.QUEEN, cell=piece.cell)
