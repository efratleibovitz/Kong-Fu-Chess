# realtime/move_settler.py
from model.game_state import GameState
from model.piece import PieceKind
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

        for piece, from_pos, to_pos, arrive_time, _, _ in bounced:
            board.set_piece(from_pos, piece)
            state.cooldowns[(from_pos.col, from_pos.row)] = arrive_time + SHORT_REST_MS
            state.rest_type[(from_pos.col, from_pos.row)] = 'short_rest'

        # jump interception
        surviving_moves = []
        for move in settled:
            piece, from_pos, to_pos, _, _, _ = move
            color_char = 'w' if piece.color.value == 'white' else 'b'
            jump_at_dest = any(
                j[1] == to_pos and j[0].color != piece.color
                for j in expired_jumps
            )
            if jump_at_dest:
                board.set_piece(from_pos, None)
                jumping_piece = next(j[0] for j in expired_jumps if j[1] == to_pos and j[0].color != piece.color)
                jumping_color = 'w' if jumping_piece.color.value == 'white' else 'b'
                state.captured[jumping_color].append(piece)
                state.scores[jumping_color] += PIECE_VALUES.get(piece.kind, 0)
            else:
                surviving_moves.append(move)

        settled = surviving_moves

        for piece, from_pos, to_pos, arrive_time, _depart, mid_path_captures in settled:
            color_char = 'w' if piece.color.value == 'white' else 'b'
            occupant = board.get_piece(to_pos)
            if occupant is not None and occupant.color == piece.color:
                # friendly piece already there — bounce back
                board.set_piece(from_pos, piece)
                state.cooldowns[(from_pos.col, from_pos.row)] = arrive_time + SHORT_REST_MS
                state.rest_type[(from_pos.col, from_pos.row)] = 'short_rest'
                continue

            if any(CaptureRules.is_king_captured(cap[0]) for cap in mid_path_captures):
                state.game_over = True
                for cap, _ in mid_path_captures:
                    if CaptureRules.is_king_captured(cap):
                        state.loser = 'w' if cap.color.value == 'white' else 'b'

            for cap_piece, cap_pos in mid_path_captures:
                board.set_piece(cap_pos, None)
                state.captured[color_char].append(cap_piece)
                state.scores[color_char] += PIECE_VALUES.get(cap_piece.kind, 0)

            captured = board.get_piece(to_pos)
            board.set_piece(from_pos, None)
            board.set_piece(to_pos, piece)

            if captured is not None and captured.color != piece.color:
                state.captured[color_char].append(captured)
                state.scores[color_char] += PIECE_VALUES.get(captured.kind, 0)

            if CaptureRules.is_king_captured(captured):
                state.game_over = True
                state.loser = 'w' if captured.color.value == 'white' else 'b'
                state.events.emit('game_over', loser=state.loser)

            if CaptureRules.should_promote(piece, to_pos, board):
                promoted = CaptureRules.promote(piece)
                board.set_piece(to_pos, promoted)

            is_king = CaptureRules.is_king_captured(captured) or any(CaptureRules.is_king_captured(c[0]) for c in mid_path_captures)
            is_queen = (captured is not None and captured.kind == PieceKind.QUEEN) or any(c[0].kind == PieceKind.QUEEN for c in mid_path_captures)
            notation = move_to_notation(
                piece.kind.value, from_pos.col, from_pos.row, to_pos.col, to_pos.row,
                is_capture=(captured is not None and captured.color != piece.color) or bool(mid_path_captures),
                is_checkmate=is_king,
                is_check=is_queen and not is_king,
                board=board
            )
            state.move_history.append(MoveRecord(time_ms=arrive_time, notation=notation, color=color_char))

            state.cooldowns[(to_pos.col, to_pos.row)] = arrive_time + LONG_REST_MS
            state.rest_type[(to_pos.col, to_pos.row)] = 'long_rest'
            state.events.emit('piece_settled')

    @staticmethod
    def _resolve_conflicts(settled: list) -> tuple[list, list]:
        winners: dict = {}
        for move in settled:
            key = (move[2].col, move[2].row)
            if key not in winners or move[3] < winners[key][3]:
                winners[key] = move
        winner_set = set(id(m) for m in winners.values())
        losers = [m for m in settled if id(m) not in winner_set]
        return list(winners.values()), losers
