from model.piece import PieceKind

PIECE_VALUES: dict[PieceKind, int] = {
    PieceKind.PAWN:   1,
    PieceKind.KNIGHT: 3,
    PieceKind.BISHOP: 3,
    PieceKind.ROOK:   5,
    PieceKind.QUEEN:  9,
    PieceKind.KING:   0,
}
