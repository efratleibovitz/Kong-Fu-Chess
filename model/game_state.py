# model/game_state.py
from dataclasses import dataclass, field
from model.board import Board
from model.position import Position

@dataclass
class GameState:
    board: Board
    clock: int = 0
    pending_moves: list = field(default_factory=list)
    pending_jumps: list = field(default_factory=list)
    game_over: bool = False
    selected_position: Position | None = None