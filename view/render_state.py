from dataclasses import dataclass, field
from typing import Optional
from view.constants import PieceState


@dataclass
class PieceRenderInfo:
    token: str
    col: int
    row: int
    state: PieceState
    cooldown_fill: float        # 0.0-1.0, 0 means no bar
    cooldown_is_long: bool


@dataclass
class MoveArrow:
    to_col: int
    to_row: int


@dataclass
class PlayerRenderInfo:
    name: str
    score: int
    captured: list[str]
    move_history: list          # list of (time_ms: int, notation: str)


@dataclass
class RenderState:
    # board
    num_cols: int
    num_rows: int
    pieces: list[PieceRenderInfo]
    selected_col: Optional[int]
    selected_row: Optional[int]
    pending_destinations: list[MoveArrow]

    # hud
    clock_ms: int
    white: PlayerRenderInfo
    black: PlayerRenderInfo

    # overlay
    game_over: bool
    loser: Optional[str]        # 'w' or 'b'

    # transient client-side UI feedback (e.g. "Not your piece") - never
    # sent by the server, only ever set locally by NetworkSession after
    # decoding its own RenderState
    message: Optional[str] = None
