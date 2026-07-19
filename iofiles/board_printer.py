from model.board import Board
from model.position import Position

def print_board(board: Board):
    for r in range(board.num_rows):
        print(' '.join(board.get_token(Position(c, r)) for c in range(board.num_cols)))
