import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.moves.KingMove import KingMove
from core.moves.RookMove import RookMove
from core.moves.move_factory import MoveFactory


def test_move_factory_loads_strategy_map_from_config(tmp_path):
    config_path = tmp_path / 'move_config.json'
    config_path.write_text(json.dumps({'K': 'KingMove', 'R': 'RookMove'}), encoding='utf-8')

    original_strategies = MoveFactory._strategies
    try:
        MoveFactory._strategies = {}
        strategies = MoveFactory.load_from_config(config_path)

        assert isinstance(strategies['K'], KingMove)
        assert isinstance(strategies['R'], RookMove)
        assert MoveFactory.get_strategy('K') is not None
    finally:
        MoveFactory._strategies = original_strategies
