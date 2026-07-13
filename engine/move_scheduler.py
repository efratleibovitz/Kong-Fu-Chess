# engine/move_scheduler.py
from model.game_state import GameState
from model.position import Position
from model.board import Board


class MoveScheduler:
    """Handles scheduling of moves: conflict detection, timing, interception."""

    @staticmethod
    def _columns_of(from_pos: Position, to_pos: Position) -> set:
        min_col = min(from_pos.col, to_pos.col)
        max_col = max(from_pos.col, to_pos.col)
        return set(range(min_col, max_col + 1))

    @staticmethod
    def has_column_conflict(from_pos: Position, to_pos: Position, state: GameState) -> bool:
        new_cols = MoveScheduler._columns_of(from_pos, to_pos)
        for _, pf, pt, _ in state.pending_moves:
            if new_cols & MoveScheduler._columns_of(pf, pt):
                return True
        return False

    @staticmethod
    def schedule(from_pos: Position, to_pos: Position, state: GameState):
        board = state.board
        token = board.get_token(from_pos)
        distance = max(abs(to_pos.col - from_pos.col), abs(to_pos.row - from_pos.row))
        arrive_time = state.clock + distance * 500

        intercepted = any(
            j[1] == to_pos and j[0][0] != token[0]
            for j in state.pending_jumps
        )

        if intercepted:
            board.set_token(from_pos, '.')
        else:
            state.pending_moves.append((token, from_pos, to_pos, arrive_time))
