from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from model.board import Board
from model.position import Position
from model.move_record import MoveRecord


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