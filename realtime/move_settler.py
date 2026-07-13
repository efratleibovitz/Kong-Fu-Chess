# realtime/move_settler.py
from model.game_state import GameState
from rules.capture_rules import CaptureRules


class MoveSettler:
    """Advances the clock and settles any moves that have arrived."""

    @staticmethod
    def settle(state: GameState, ms: int):
        state.clock += ms
        board = state.board

        settled = [m for m in state.pending_moves if m[3] <= state.clock]
        state.pending_moves = [m for m in state.pending_moves if m[3] > state.clock]
        state.pending_jumps = [j for j in state.pending_jumps if j[2] > state.clock]

        for token, from_pos, to_pos, _ in settled:
            captured = board.get_token(to_pos)
            board.set_token(from_pos, '.')
            board.set_token(to_pos, token)

            if CaptureRules.is_king_captured(captured):
                state.game_over = True

            if CaptureRules.should_promote(token, to_pos, board):
                board.set_token(to_pos, CaptureRules.promote(token))
