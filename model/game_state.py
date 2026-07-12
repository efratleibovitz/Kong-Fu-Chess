from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from model.board import Board
from model.position import Position


@dataclass
class GameState:
    board: Board
    clock: int = 0
    game_over: bool = False
    selected_position: Optional[Position] = None
    pending_moves: List[Tuple[str, Position, Position, int]] = field(default_factory=list)
    pending_jumps: List[Tuple[str, Position, int]] = field(default_factory=list)
