from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from model.board import Board
from model.position import Position
from model.move_record import MoveRecord
from model.event_bus import EventBus


@dataclass
class GameState:
    board: Board
    clock: int = 0
    game_over: bool = False
    selected_position: Optional[Position] = None
    pending_moves: List[Tuple[str, Position, Position, int, int, List[str]]] = field(default_factory=list)
    pending_jumps: List[Tuple[str, Position, int]] = field(default_factory=list)
    cooldowns: Dict[Tuple[int,int], int] = field(default_factory=dict)
    player_names: Dict[str, str] = field(default_factory=lambda: {'w': 'White', 'b': 'Black'})
    captured: Dict[str, List[str]] = field(default_factory=lambda: {'w': [], 'b': []})
    scores: Dict[str, int] = field(default_factory=lambda: {'w': 0, 'b': 0})
    rest_type: Dict[Tuple[int,int], str] = field(default_factory=dict)
    loser: Optional[str] = None
    move_history: List[MoveRecord] = field(default_factory=list)
    events: EventBus = field(default_factory=EventBus)

    def to_render_state(self):
        from view.render_state import RenderState, PieceRenderInfo, MoveArrow, PlayerRenderInfo
        from view.constants import PieceState

        moving = {(m[1].col, m[1].row) for m in self.pending_moves}
        jumping = {(j[1].col, j[1].row) for j in self.pending_jumps}
        LONG_REST_MS = 2000
        SHORT_REST_MS = 1000

        pieces = []
        for row_i, row in enumerate(self.board.rows):
            for col_i, token in enumerate(row):
                if token == '.':
                    continue
                key = (col_i, row_i)
                if key in moving:
                    ps = PieceState.MOVE
                elif key in jumping:
                    ps = PieceState.JUMP
                elif self.cooldowns.get(key, 0) > self.clock:
                    rest = self.rest_type.get(key, 'long_rest')
                    ps = PieceState.LONG_REST if rest == 'long_rest' else PieceState.SHORT_REST
                else:
                    ps = PieceState.IDLE

                expire = self.cooldowns.get(key, 0)
                if expire > self.clock:
                    rest = self.rest_type.get(key, 'long_rest')
                    total_ms = LONG_REST_MS if rest == 'long_rest' else SHORT_REST_MS
                    fill = max(0.0, min(1.0, (expire - self.clock) / total_ms))
                    is_long = rest == 'long_rest'
                else:
                    fill = 0.0
                    is_long = False

                pieces.append(PieceRenderInfo(token, col_i, row_i, ps, fill, is_long))

        def _player(color: str) -> PlayerRenderInfo:
            return PlayerRenderInfo(
                name=self.player_names[color],
                score=self.scores[color],
                captured=list(self.captured[color]),
                move_history=[(m.time_ms, m.notation) for m in self.move_history if m.color == color]
            )

        return RenderState(
            num_cols=self.board.num_cols,
            num_rows=self.board.num_rows,
            pieces=pieces,
            selected_col=self.selected_position.col if self.selected_position else None,
            selected_row=self.selected_position.row if self.selected_position else None,
            pending_destinations=[MoveArrow(m[2].col, m[2].row) for m in self.pending_moves],
            clock_ms=self.clock,
            white=_player('w'),
            black=_player('b'),
            game_over=self.game_over,
            loser=self.loser,
        )