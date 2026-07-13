# from typing import List, Optional, Tuple
# from dataclasses import dataclass, field
# from model.board import Board
# from model.position import Position


# @dataclass
# class GameState:
#     board: Board
#     clock: int = 0
#     game_over: bool = False
#     selected_position: Optional[Position] = None
#     # tuple: (token, from_pos, to_pos, arrive_time, depart_time)
#     pending_moves: List[Tuple[str, Position, Position, int, int]] = field(default_factory=list)
#     pending_jumps: List[Tuple[str, Position, int]] = field(default_factory=list)
#     # tokens captured mid-path during scheduling (e.g. king) — checked at settle time
#     mid_path_captures: List[str] = field(default_factory=list)


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
    # tuple: (token, from_pos, to_pos, arrive_time, depart_time, mid_path_captures)
    pending_moves: List[Tuple[str, Position, Position, int, int, List[str]]] = field(default_factory=list)
    pending_jumps: List[Tuple[str, Position, int]] = field(default_factory=list)