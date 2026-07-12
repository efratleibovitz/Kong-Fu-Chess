import json
from pathlib import Path

from rules.moves.KingMove import KingMove
from rules.moves.RookMove import RookMove
from rules.moves.BishopMove import BishopMove
from rules.moves.QueenMove import QueenMove
from rules.moves.KnightMove import KnightMove
from rules.moves.PawnMove import PawnMove


class MoveFactory:
    _strategies = {}

    @classmethod
    def load_from_config(cls, config_path=None):
        if config_path is None:
            config_path = Path(__file__).resolve().parent / 'move_config.json'

        with open(config_path, 'r', encoding='utf-8') as file:
            config = json.load(file)

        strategy_map = {}
        for piece_type, class_name in config.items():
            strategy_class = globals()[class_name]
            strategy_map[piece_type] = strategy_class()

        cls._strategies = strategy_map
        return strategy_map

    @classmethod
    def get_strategy(cls, piece_type: str):
        if not cls._strategies:
            cls.load_from_config()
        return cls._strategies.get(piece_type)
