from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from model.board import Board
from model.position import Position


@dataclass
class GameState:
    board: Board
    clock: int = 0
    game_over: bool = False
    selected_position: Optional[Position] = None
    # tuple: (token, from_pos, to_pos, arrive_time, depart_time, mid_path_captures)
    pending_moves: List[Tuple[str, Position, Position, int, int, List[str]]] = field(default_factory=list)
    pending_jumps: List[Tuple[str, Position, int]] = field(default_factory=list)
    # (col,row) -> clock time when cooldown expires
    cooldowns: Dict[Tuple[int,int], int] = field(default_factory=dict)
    # player names
    player_names: Dict[str, str] = field(default_factory=lambda: {'w': 'White', 'b': 'Black'})
    # captured pieces per player  e.g. {'w': ['bP', 'bR'], 'b': ['wP']}
    captured: Dict[str, List[str]] = field(default_factory=lambda: {'w': [], 'b': []})
    # score per player
    scores: Dict[str, int] = field(default_factory=lambda: {'w': 0, 'b': 0})
    # (col,row) -> rest animation type ('long_rest' or 'short_rest')
    rest_type: Dict[Tuple[int,int], str] = field(default_factory=dict)
    # color of the player who lost ('w' or 'b'), None if game not over
    loser: Optional[str] = None