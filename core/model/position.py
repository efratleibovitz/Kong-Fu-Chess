from dataclasses import dataclass


@dataclass
class Position:
    col: int
    row: int

    @property
    def x(self) -> int:
        return self.col

    @property
    def y(self) -> int:
        return self.row
