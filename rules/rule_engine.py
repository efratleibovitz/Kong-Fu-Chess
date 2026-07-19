# rules/rule_engine.py
from model.board import Board
from rules.moves.move_factory import MoveFactory


class RuleEngine:
    def validate_move(self, board: Board, from_pos, to_pos):
        # 1. בדיקת גבולות לוח
        if not board.is_within_bounds(from_pos) or not board.is_within_bounds(to_pos):
            return {"is_valid": False, "reason": "outside_board"}
        
        # 2. האם יש כלי במקור?
        piece = board.get_piece(from_pos)
        if piece is None:
            return {"is_valid": False, "reason": "empty_source"}
        
        # 3. האם היעד תפוס ע"י כלי ידידותי?
        dest_piece = board.get_piece(to_pos)
        if dest_piece is not None and dest_piece.color == piece.color:
            return {"is_valid": False, "reason": "friendly_destination"}
        
        # 4. בדיקת חוקיות גיאומטרית (Strategy Pattern)
        strategy = MoveFactory.get_strategy(piece.kind.value)
        if not strategy or not strategy.is_valid(from_pos, to_pos, board):
            return {"is_valid": False, "reason": "illegal_piece_move"}
            
        return {"is_valid": True, "reason": "ok"}