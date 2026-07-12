from dataclasses import dataclass, field
from model.board import Board
from model.position import Position


@dataclass
class GameState:
    board: Board
    clock: int = 0
    game_over: bool = False
    selected_position: Position | None = None
