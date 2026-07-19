import re
from model.piece import Piece
from model.position import Position

VALID_TOKEN = re.compile(r'^[wb][KQRBNP]$|^\.$')

def parse_input(lines):
    board_lines = []
    command_lines = []
    section = None

    for line in lines:
        stripped = line.strip()
        if stripped == 'Board:':
            section = 'board'
        elif stripped == 'Commands:':
            section = 'commands'
        elif section == 'board':
            board_lines.append(stripped)
        elif section == 'commands':
            command_lines.append(stripped)

    return board_lines, command_lines

def validate_board(board_lines):
    rows = [line.split() for line in board_lines if line.strip()]
    if not rows:
        return None, None

    width = len(rows[0])
    for row in rows:
        if len(row) != width:
            return None, 'ROW_WIDTH_MISMATCH'
        for token in row:
            if not VALID_TOKEN.match(token):
                return None, 'UNKNOWN_TOKEN'

    piece_rows = [
        [Piece.from_token(t, Position(c, r)) if t != '.' else None
         for c, t in enumerate(row)]
        for r, row in enumerate(rows)
    ]
    return piece_rows, None
