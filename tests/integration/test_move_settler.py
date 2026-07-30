import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.model.board import Board
from core.model.position import Position
from core.model.game_state import GameState
from core.engine.game_engine import GameEngine


def _make(rows):
    return GameEngine(GameState(Board(rows)))


# ---------------------------------------------------------------------------
# Bounce-back: friendly piece occupies destination on arrival
# ---------------------------------------------------------------------------

def test_piece_bounces_back_when_friendly_arrives_first():
    # Two white pieces target the same square simultaneously.
    # wR at (0,0) → (2,0): distance=2, arrives t=1000.
    # wP at (4,0) → (2,0): distance=2, arrives t=1000.
    # _resolve_conflicts picks the first one scheduled (wR); wP is the loser
    # and bounces back to its from_pos with a short cooldown.
    game = _make([['wR', '.', '.', '.', 'wP']])
    game.click(50, 50)    # select wR at (0,0)
    game.click(250, 50)   # wR → (2,0)
    game.click(450, 50)   # select wP at (4,0)
    game.click(250, 50)   # wP → (2,0) — same target, same arrival time
    game.wait(2000)
    # wR wins (scheduled first), wP bounces back to (4,0)
    assert game.board.get_token(Position(2, 0)) == 'wR'
    assert game.board.get_token(Position(4, 0)) == 'wP'


# ---------------------------------------------------------------------------
# Mid-path king capture triggers game_over
# ---------------------------------------------------------------------------

def test_mid_path_king_capture_ends_game():
    # wR at col=0 moves right, bK at col=1 is in the path
    game = _make([['wR', 'bK', '.', '.']])
    game.click(50, 50)
    game.click(350, 50)   # wR targets col=3, bK at col=1 is mid-path capture
    game.wait(2000)
    assert game.state.game_over is True
    assert game.state.loser == 'b'


# ---------------------------------------------------------------------------
# Restart resets game state
# ---------------------------------------------------------------------------

def test_restart_resets_board_and_clock():
    game = _make([['wR', '.', 'bK']])
    game.click(50, 50)
    game.click(250, 50)
    game.wait(1000)
    game.restart()
    assert game.board.get_token(Position(0, 0)) == 'wR'
    assert game.board.get_token(Position(2, 0)) == 'bK'
    assert game.state.clock == 0
    assert game.state.game_over is False


def test_restart_clears_pending_moves():
    game = _make([['wR', '.', '.']])
    game.click(50, 50)
    game.click(250, 50)
    assert len(game.pending_moves) == 1
    game.restart()
    assert len(game.pending_moves) == 0


# ---------------------------------------------------------------------------
# jump_cell (server path) — missing coverage in game_engine
# ---------------------------------------------------------------------------

def test_jump_cell_valid():
    game = _make([['.', '.', '.'], ['.', 'wK', '.'], ['.', '.', '.']])
    game.jump_cell(1, 1, 'w')
    assert len(game.pending_jumps) == 1


def test_jump_cell_wrong_color_ignored():
    game = _make([['.', '.', '.'], ['.', 'wK', '.'], ['.', '.', '.']])
    game.jump_cell(1, 1, 'b')   # black tries to jump white king
    assert len(game.pending_jumps) == 0


def test_jump_cell_out_of_bounds_ignored():
    game = _make([['.', 'wK', '.']])
    game.jump_cell(99, 99, 'w')
    assert len(game.pending_jumps) == 0
