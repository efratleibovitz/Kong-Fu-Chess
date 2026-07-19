# engine/move_scheduler.py
from model.game_state import GameState
from model.position import Position
from model.piece import PieceKind
from rules.collision_rules import CollisionRules, StepResult


class MoveScheduler:
    """Handles scheduling of moves: conflict detection, timing, interception."""

    @staticmethod
    def _columns_of(from_pos: Position, to_pos: Position) -> set:
        min_col = min(from_pos.col, to_pos.col)
        max_col = max(from_pos.col, to_pos.col)
        return set(range(min_col, max_col + 1))

    @staticmethod
    def has_column_conflict(from_pos: Position, to_pos: Position, state: GameState) -> bool:
        if from_pos.row != to_pos.row:
            return False
        new_cols = MoveScheduler._columns_of(from_pos, to_pos)
        for _, pf, pt, _, _, _ in state.pending_moves:
            if pf.row == pt.row == from_pos.row:
                if new_cols & MoveScheduler._columns_of(pf, pt):
                    return True
        return False

    @staticmethod
    def _build_path(from_pos: Position, to_pos: Position) -> list[Position]:
        """Returns each square on the path from from_pos to to_pos (excluding start)."""
        steps = []
        dc = to_pos.col - from_pos.col
        dr = to_pos.row - from_pos.row
        step_count = max(abs(dc), abs(dr))
        if step_count == 0:
            return steps
        col_step = dc // step_count if dc != 0 else 0
        row_step = dr // step_count if dr != 0 else 0
        cur = from_pos
        for _ in range(step_count):
            cur = Position(cur.col + col_step, cur.row + row_step)
            steps.append(cur)
        return steps

    @staticmethod
    def schedule(from_pos: Position, to_pos: Position, state: GameState):
        board = state.board
        piece = board.get_piece(from_pos)
        depart_time = state.clock
        is_knight = piece.kind == PieceKind.KNIGHT

        if is_knight:
            actual_to = to_pos
            mid_path_captures: list = []
        else:
            path = MoveScheduler._build_path(from_pos, to_pos)
            actual_to = from_pos
            mid_path_captures = []
            for step in path:
                result = CollisionRules.check_step(step, piece, board)
                if result == StepResult.CLEAR:
                    actual_to = step
                elif result == StepResult.CAPTURE:
                    cap_piece = board.get_piece(step)
                    mid_path_captures.append((cap_piece, step))
                    actual_to = step
                elif result == StepResult.BLOCKED:
                    break

            if actual_to == from_pos:
                return

        distance = max(abs(actual_to.col - from_pos.col), abs(actual_to.row - from_pos.row))
        arrive_time = depart_time + distance * 500
        state.pending_moves.append((piece, from_pos, actual_to, arrive_time, depart_time, mid_path_captures))
