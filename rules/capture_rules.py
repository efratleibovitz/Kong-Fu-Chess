# rules/capture_rules.py
from model.board import Board
from model.position import Position


class CaptureRules:



    @staticmethod
    def is_king_captured(token: str) -> bool:
        #!!!
        return token != '.' and token[1] == 'K'

    @staticmethod
    def should_promote(token: str, to_pos: Position, board: Board) -> bool:
        if token[1] != 'P':
            return False
        promote_row = 0 if token[0] == 'w' else board.num_rows - 1
        return to_pos.row == promote_row

    @staticmethod
    def promote(token: str) -> str:
        return token[0] + 'Q'
