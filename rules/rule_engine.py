# rules/rule_engine.py
from model.board import Board
from rules.moves.move_factory import MoveFactory


class RuleEngine:
    def validate_move(self, board: Board, from_pos, to_pos):
        # 1. בדיקת גבולות לוח
        if not board.is_within_bounds(from_pos) or not board.is_within_bounds(to_pos):
            return {"is_valid": False, "reason": "outside_board"}
        
        # 2. האם יש כלי במקור?
        token = board.get_token(from_pos)
        if token == '.':
            return {"is_valid": False, "reason": "empty_source"}
        
        # 3. האם היעד תפוס ע"י כלי ידידותי?
        dest_token = board.get_token(to_pos)
        if dest_token != '.' and dest_token[0] == token[0]:
            return {"is_valid": False, "reason": "friendly_destination"}
        
        # 4. בדיקת חוקיות גיאומטרית (Strategy Pattern)
        strategy = MoveFactory.get_strategy(token[1])
        if not strategy or not strategy.is_valid(from_pos, to_pos, board):
            return {"is_valid": False, "reason": "illegal_piece_move"}
            
        return {"is_valid": True, "reason": "ok"}