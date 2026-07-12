from model.board import Board

def print_board(board: Board):
    for row in board.rows:
        print(' '.join(row))
