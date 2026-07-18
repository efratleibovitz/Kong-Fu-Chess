# realtime/move_settler.py
from model.game_state import GameState
from rules.capture_rules import CaptureRules
from model.piece_values import PIECE_VALUES
from model.move_record import MoveRecord
from model.notation import move_to_notation

LONG_REST_MS = 2000
SHORT_REST_MS = 1000


class MoveSettler:
    """Advances the clock and settles any moves that have arrived."""

    @staticmethod
    def settle(state: GameState, ms: int):
        state.clock += ms
        board = state.board

        settled = [m for m in state.pending_moves if m[3] <= state.clock]
        state.pending_moves = [m for m in state.pending_moves if m[3] > state.clock]

        expired_jumps = [j for j in state.pending_jumps if j[2] <= state.clock]
        state.pending_jumps = [j for j in state.pending_jumps if j[2] > state.clock]

        for _, jump_pos, _ in expired_jumps:
            state.cooldowns[(jump_pos.col, jump_pos.row)] = state.clock + SHORT_REST_MS
            state.rest_type[(jump_pos.col, jump_pos.row)] = 'short_rest'

        settled, bounced = MoveSettler._resolve_conflicts(settled)

        for token, from_pos, to_pos, arrive_time, _, _ in bounced:
            board.set_token(from_pos, token)
            state.cooldowns[(from_pos.col, from_pos.row)] = arrive_time + SHORT_REST_MS
            state.rest_type[(from_pos.col, from_pos.row)] = 'short_rest'

        for token, from_pos, to_pos, arrive_time, _, _ in settled:
            pass

        # jump interception — remove any settled move whose destination has an active enemy jump
        surviving_moves = []
        for move in settled:
            token, from_pos, to_pos, _, _, _ = move
            jump_at_dest = any(
                j[1] == to_pos and j[0][0] != token[0]
                for j in state.pending_jumps
            )
            if jump_at_dest:
                board.set_token(from_pos, '.')  # intercepted piece is destroyed
                jumping_color = next(j[0][0] for j in state.pending_jumps if j[1] == to_pos and j[0][0] != token[0])
                state.captured[jumping_color].append(token)
                state.scores[jumping_color] += PIECE_VALUES.get(token[1], 0)
            else:
                surviving_moves.append(move)

        settled = surviving_moves

        for token, from_pos, to_pos, arrive_time, _depart, mid_path_captures in settled:
            occupant = board.get_token(to_pos)
            if occupant != '.' and occupant[0] == token[0]:
                # friendly piece already there (arrived in a previous frame) — bounce back
                board.set_token(from_pos, token)
                state.cooldowns[(from_pos.col, from_pos.row)] = arrive_time + SHORT_REST_MS
                state.rest_type[(from_pos.col, from_pos.row)] = 'short_rest'
                continue
            if any(CaptureRules.is_king_captured(cap[0]) for cap in mid_path_captures):
                state.game_over = True
                for cap, _ in mid_path_captures:
                    if CaptureRules.is_king_captured(cap):
                        state.loser = cap[0]

            for cap_token, cap_pos in mid_path_captures:
                board.set_token(cap_pos, '.')
                state.captured[token[0]].append(cap_token)
                state.scores[token[0]] += PIECE_VALUES.get(cap_token[1], 0)

            captured = board.get_token(to_pos)
            board.set_token(from_pos, '.')
            board.set_token(to_pos, token)

            if captured != '.' and captured[0] != token[0]:
                state.captured[token[0]].append(captured)
                state.scores[token[0]] += PIECE_VALUES.get(captured[1], 0)

            if CaptureRules.is_king_captured(captured):
                state.game_over = True
                state.loser = captured[0]
                state.events.emit('game_over', loser=state.loser)

            if CaptureRules.should_promote(token, to_pos, board):
                board.set_token(to_pos, CaptureRules.promote(token))

            is_king = CaptureRules.is_king_captured(captured) or any(CaptureRules.is_king_captured(c[0]) for c in mid_path_captures)
            is_queen = (captured != '.' and captured[1] == 'Q') or any(c[0][1] == 'Q' for c in mid_path_captures)
            notation = move_to_notation(
                token[1], from_pos.col, from_pos.row, to_pos.col, to_pos.row,
                is_capture=(captured != '.' and captured[0] != token[0]) or bool(mid_path_captures),
                is_checkmate=is_king,
                is_check=is_queen and not is_king,
                board=board
            )
            state.move_history.append(MoveRecord(time_ms=arrive_time, notation=notation, color=token[0]))

            state.cooldowns[(to_pos.col, to_pos.row)] = arrive_time + LONG_REST_MS
            state.rest_type[(to_pos.col, to_pos.row)] = 'long_rest'
            state.events.emit('piece_settled')

    @staticmethod
    def _step_before(from_pos, to_pos):
        """Returns the square one step before to_pos along the from_pos→to_pos path."""
        from model.position import Position
        dc = to_pos.col - from_pos.col
        dr = to_pos.row - from_pos.row
        dist = max(abs(dc), abs(dr))
        if dist <= 1:
            return from_pos
        col_step = (dc // abs(dc)) if dc != 0 else 0
        row_step = (dr // abs(dr)) if dr != 0 else 0
        return Position(to_pos.col - col_step, to_pos.row - row_step)

    @staticmethod
    def _resolve_conflicts(settled: list) -> tuple[list, list]:
        """
        Among moves landing on the same square, keep only the one
        with the earliest depart_time (index 4). Return (winners, losers).
        """
        winners: dict = {}
        for move in settled:
            key = (move[2].col, move[2].row)
            if key not in winners or move[3] < winners[key][3]:
                winners[key] = move
        winner_set = set(id(m) for m in winners.values())
        losers = [m for m in settled if id(m) not in winner_set]
        return list(winners.values()), losers