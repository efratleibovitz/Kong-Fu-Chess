from dataclasses import dataclass


@dataclass
class MoveRecord:
    time_ms: int    # state.clock when the move settled
    notation: str   # algebraic notation string e.g. "Nxe4+", "O-O"
    color: str      # 'w' or 'b' — from token[0]
