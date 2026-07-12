from dataclasses import dataclass
from model.position import Position


@dataclass
class Motion:
    token: str
    from_pos: Position
    to_pos: Position
    arrive_time: int  # absolute clock time when this motion arrives


@dataclass
class Jump:
    token: str
    pos: Position
    expire_time: int  # absolute clock time when the jump window closes
