# # engine/move_scheduler.py
# from model.game_state import GameState
# from model.position import Position
# from rules.collision_rules import CollisionRules, StepResult


# class MoveScheduler:
#     """Handles scheduling of moves: conflict detection, timing, interception."""

#     @staticmethod
#     def _columns_of(from_pos: Position, to_pos: Position) -> set:
#         min_col = min(from_pos.col, to_pos.col)
#         max_col = max(from_pos.col, to_pos.col)
#         return set(range(min_col, max_col + 1))

#     @staticmethod
#     def has_column_conflict(from_pos: Position, to_pos: Position, state: GameState) -> bool:
#         new_cols = MoveScheduler._columns_of(from_pos, to_pos)
#         for _, pf, pt, _, _ in state.pending_moves:
#             if new_cols & MoveScheduler._columns_of(pf, pt):
#                 return True
#         return False

#     @staticmethod
#     def _build_path(from_pos: Position, to_pos: Position) -> list[Position]:
#         """Returns each square on the path from from_pos to to_pos (excluding start)."""
#         steps = []
#         dc = to_pos.col - from_pos.col
#         dr = to_pos.row - from_pos.row
#         step_count = max(abs(dc), abs(dr))
#         if step_count == 0:
#             return steps
#         col_step = dc // step_count if dc != 0 else 0
#         row_step = dr // step_count if dr != 0 else 0
#         cur = from_pos
#         for _ in range(step_count):
#             cur = Position(cur.col + col_step, cur.row + row_step)
#             steps.append(cur)
#         return steps

#     @staticmethod
#     def schedule(from_pos: Position, to_pos: Position, state: GameState):
#         board = state.board
#         token = board.get_token(from_pos)
#         depart_time = state.clock

#         # Check for jump interception at destination
#         intercepted = any(
#             j[1] == to_pos and j[0][0] != token[0]
#             for j in state.pending_jumps
#         )
#         if intercepted:
#             board.set_token(from_pos, '.')
#             return

#         # Walk path step by step — captures are removed immediately,
#         # king captures are stored for MoveSettler to set game_over at settle time.
#         path = MoveScheduler._build_path(from_pos, to_pos)
#         actual_to = from_pos
#         for step in path:
#             result = CollisionRules.check_step(step, token, board)
#             if result == StepResult.CLEAR:
#                 actual_to = step
#             elif result == StepResult.CAPTURE:
#                 captured = board.get_token(step)
#                 state.mid_path_captures.append(captured)  # settler checks for king
#                 board.set_token(step, '.')                 # remove enemy; piece continues
#                 actual_to = step
#             elif result == StepResult.BLOCKED:
#                 break

#         if actual_to == from_pos:
#             return  # immediately blocked, no move

#         distance = max(abs(actual_to.col - from_pos.col), abs(actual_to.row - from_pos.row))
#         arrive_time = depart_time + distance * 500
#         state.pending_moves.append((token, from_pos, actual_to, arrive_time, depart_time))


# engine/move_scheduler.py
from model.game_state import GameState
from model.position import Position
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
        new_cols = MoveScheduler._columns_of(from_pos, to_pos)
        for _, pf, pt, _, _, _ in state.pending_moves:
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
        token = board.get_token(from_pos)
        depart_time = state.clock

        # Check for jump interception at destination
        intercepted = any(
            j[1] == to_pos and j[0][0] != token[0]
            for j in state.pending_jumps
        )
        if intercepted:
            board.set_token(from_pos, '.')
            return

        # Walk path step by step — captures are removed immediately,
        # but king captures are stored PER-MOVE and only affect game_over
        # once this specific move actually settles (see MoveSettler).
        path = MoveScheduler._build_path(from_pos, to_pos)
        actual_to = from_pos
        mid_path_captures: list[str] = []
        for step in path:
            result = CollisionRules.check_step(step, token, board)
            if result == StepResult.CLEAR:
                actual_to = step
            elif result == StepResult.CAPTURE:
                captured = board.get_token(step)
                mid_path_captures.append(captured)
                board.set_token(step, '.')               # remove enemy; piece continues
                actual_to = step
            elif result == StepResult.BLOCKED:
                break

        if actual_to == from_pos:
            return  # immediately blocked, no move

        distance = max(abs(actual_to.col - from_pos.col), abs(actual_to.row - from_pos.row))
        arrive_time = depart_time + distance * 500
        state.pending_moves.append((token, from_pos, actual_to, arrive_time, depart_time, mid_path_captures))