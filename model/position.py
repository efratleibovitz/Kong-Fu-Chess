from dataclasses import dataclass


@dataclass
class Position:
    col: int
    row: int

    # backward-compat aliases so existing code using .x/.y still works
    @property
    def x(self) -> int:
        return self.col

    @property
    def y(self) -> int:
        return self.row
