from dataclasses import dataclass, field
from model.board import Board
from model.position import Position


@dataclass
class GameState:
    board: Board
    clock: int = 0
    game_over: bool = False
    selected_position: Position | None = None
    pending_moves: list[tuple[str, Position, Position, int]] = field(default_factory=list)
    pending_jumps: list[tuple[str, Position, int]] = field(default_factory=list)
