# realtime/move_settler.py
from model.game_state import GameState
from rules.capture_rules import CaptureRules

LONG_REST_MS = 1500
SHORT_REST_MS = 600


class MoveSettler:
    """Advances the clock and settles any moves that have arrived."""

    @staticmethod
    def settle(state: GameState, ms: int):
        state.clock += ms
        board = state.board

        settled = [m for m in state.pending_moves if m[3] <= state.clock]
        state.pending_moves = [m for m in state.pending_moves if m[3] > state.clock]
        state.pending_jumps = [j for j in state.pending_jumps if j[2] > state.clock]

        # Same-slot priority: if two pieces arrive at the same square,
        # the one that departed earlier wins; the later one is discarded.
        settled = MoveSettler._resolve_conflicts(settled)

        for token, from_pos, to_pos, arrive_time, _depart, mid_path_captures in settled:
            if any(CaptureRules.is_king_captured(t) for t in mid_path_captures):
                state.game_over = True

            captured = board.get_token(to_pos)
            board.set_token(from_pos, '.')
            board.set_token(to_pos, token)

            if CaptureRules.is_king_captured(captured):
                state.game_over = True

            if CaptureRules.should_promote(token, to_pos, board):
                board.set_token(to_pos, CaptureRules.promote(token))

            state.cooldowns[token] = arrive_time + LONG_REST_MS

        # expire jump cooldowns
        for jump_token, _, expire in list(state.pending_jumps):
            if expire <= state.clock:
                state.cooldowns[jump_token] = state.clock + SHORT_REST_MS

    @staticmethod
    def _resolve_conflicts(settled: list) -> list:
        """
        Among moves landing on the same square, keep only the one
        with the earliest depart_time (index 4). Discard the rest.
        """
        winners: dict = {}
        for move in settled:
            key = (move[2].col, move[2].row)  # Position is not hashable, use tuple
            depart_time = move[4]
            if key not in winners or depart_time < winners[key][4]:
                winners[key] = move
        return list(winners.values())