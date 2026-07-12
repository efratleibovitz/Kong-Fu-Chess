# core/moves/movement_strategy.py
from abc import ABC, abstractmethod
from model.position import Position

class MovementStrategy(ABC):
    @abstractmethod
    def is_valid(self, from_pos: Position, to_pos: Position, board) -> bool:
        pass