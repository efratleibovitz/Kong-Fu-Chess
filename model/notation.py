from model.board import Board

COL_LETTERS = 'abcdefgh'


def square_name(col: int, row: int) -> str:
    return f"{COL_LETTERS[col]}{8 - row}"


def move_to_notation(piece_type: str, from_col: int, from_row: int,
                     to_col: int, to_row: int,
                     is_capture: bool = False,
                     is_check: bool = False,
                     is_checkmate: bool = False,
                     is_castle_kingside: bool = False,
                     is_castle_queenside: bool = False,
                     board: Board = None) -> str:
    if is_castle_kingside:
        notation = 'O-O'
    elif is_castle_queenside:
        notation = 'O-O-O'
    else:
        target = square_name(to_col, to_row)
        capture_sign = 'x' if is_capture else ''

        if piece_type == 'P':
            notation = f"{COL_LETTERS[from_col]}{capture_sign}{target}" if is_capture else target
        else:
            disambig = _disambiguate(piece_type, from_col, from_row, to_col, to_row, board)
            notation = f"{piece_type}{disambig}{capture_sign}{target}"

    if is_checkmate:
        notation += '#'
    elif is_check:
        notation += '+'

    return notation


def _disambiguate(piece_type: str, from_col: int, from_row: int,
                  to_col: int, to_row: int, board: Board) -> str:
    """Returns a disambiguating prefix (column letter, row number, or both)
    if another piece of the same type and color could also reach to_pos.
    Runs after the board is updated so the moved piece is already at to_pos."""
    if board is None:
        return ''

    color = board.rows[to_row][to_col][0]  # piece is already at destination
    token = f"{color}{piece_type}"

    rivals = []
    for r in range(board.num_rows):
        for c in range(board.num_cols):
            if (c == to_col and r == to_row) or (c == from_col and r == from_row):
                continue
            if board.rows[r][c] == token:
                rivals.append((c, r))

    if not rivals:
        return ''

    # check which rivals could legally reach (to_col, to_row)
    from model.position import Position
    from rules.rule_engine import RuleEngine
    engine = RuleEngine()
    reachable = [
        (c, r) for c, r in rivals
        if engine.validate_move(board, Position(c, r), Position(to_col, to_row))['is_valid']
    ]

    if not reachable:
        return ''

    # disambiguate by column first, then row
    same_col = any(c == from_col for c, r in reachable)
    same_row = any(r == from_row for c, r in reachable)

    if not same_col:
        return COL_LETTERS[from_col]
    if not same_row:
        return str(8 - from_row)
    return f"{COL_LETTERS[from_col]}{8 - from_row}"
