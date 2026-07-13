import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from model.board import Board
from model.position import Position
from model.game_state import GameState
from engine.game_engine import GameEngine
from rules.collision_rules import CollisionRules, StepResult


def _make(rows):
    return GameEngine(GameState(Board(rows)))


# ─────────────────────────────────────────────
# Unit tests: CollisionRules.check_step
# ─────────────────────────────────────────────

def test_check_step_empty_square_is_clear():
    board = Board([['.', '.', '.']])
    assert CollisionRules.check_step(Position(1, 0), 'wR', board) == StepResult.CLEAR

def test_check_step_enemy_on_square_is_capture():
    board = Board([['bP', '.', '.']])
    assert CollisionRules.check_step(Position(0, 0), 'wR', board) == StepResult.CAPTURE

def test_check_step_friendly_on_square_is_blocked():
    board = Board([['wP', '.', '.']])
    assert CollisionRules.check_step(Position(0, 0), 'wR', board) == StepResult.BLOCKED

def test_check_step_black_piece_blocked_by_black():
    board = Board([['bP', '.', '.']])
    assert CollisionRules.check_step(Position(0, 0), 'bR', board) == StepResult.BLOCKED

def test_check_step_black_piece_captures_white():
    board = Board([['wP', '.', '.']])
    assert CollisionRules.check_step(Position(0, 0), 'bR', board) == StepResult.CAPTURE


# ─────────────────────────────────────────────
# Integration: BLOCKED — friendly piece in path
# ─────────────────────────────────────────────

def test_move_rejected_when_destination_is_friendly():
    # rule_engine rejects move to a friendly square before scheduler runs
    game = _make([['wR', 'wP', '.']])
    game.click(50, 50)
    game.click(150, 50)
    game.wait(1000)
    assert game.board.get_token(Position(0, 0)) == 'wR'
    assert game.board.get_token(Position(1, 0)) == 'wP'

def test_rook_stops_one_before_friendly_mid_path():
    # wR at col=0, wP at col=2, rook targets col=3
    # rule_engine allows (col=3 is empty), path-walk: col=1 CLEAR, col=2 BLOCKED → stops at col=1
    game = _make([['wR', '.', 'wP', '.']])
    game.click(50, 50)
    game.click(350, 50)   # target col=3
    game.wait(2000)
    assert game.board.get_token(Position(1, 0)) == 'wR'
    assert game.board.get_token(Position(2, 0)) == 'wP'
    assert game.board.get_token(Position(3, 0)) == '.'

def test_bishop_stops_one_before_friendly_on_diagonal():
    # wB at (0,2), wP at (2,0) — bishop targets (3,-1) invalid, use small board
    # wB at (0,2), wP at (1,1), bishop targets (2,0) — stops at (0,2) since (1,1) is blocked
    game = _make([
        ['.', '.', 'wB_target'],
        ['.', 'wP', '.'],
        ['wB', '.', '.'],
    ])
    # Actually use simpler: wB at (0,2), targets (2,0), wP at (1,1) blocks diagonal
    game = _make([
        ['.', '.', '.'],
        ['.', 'wP', '.'],
        ['wB', '.', '.'],
    ])
    game.click(50, 250)    # select wB at (0,2)
    game.click(250, 50)    # target (2,0) — diagonal path passes through (1,1) where wP sits
    game.wait(2000)
    assert game.board.get_token(Position(0, 2)) == 'wB'   # didn't move
    assert game.board.get_token(Position(1, 1)) == 'wP'
    assert game.board.get_token(Position(2, 0)) == '.'


# ─────────────────────────────────────────────
# Integration: CAPTURE — enemy piece in path
# ─────────────────────────────────────────────

def test_rook_captures_enemy_at_exact_destination():
    # wR at col=0, bP at col=2 — rook clicks on bP, lands there
    game = _make([['wR', '.', 'bP', '.']])
    game.click(50, 50)
    game.click(250, 50)
    game.wait(2000)
    assert game.board.get_token(Position(2, 0)) == 'wR'
    assert game.board.get_token(Position(0, 0)) == '.'

def test_rook_captures_enemy_mid_path_and_continues_to_target():
    # wR at col=0, bP at col=1, empty at col=2,3 — rook targets col=3
    # path-walk: col=1 CAPTURE (continues), col=2 CLEAR, col=3 CLEAR → lands at col=3
    game = _make([['wR', 'bP', '.', '.']])
    game.click(50, 50)
    game.click(350, 50)   # target col=3
    game.wait(2000)
    assert game.board.get_token(Position(3, 0)) == 'wR'
    assert game.board.get_token(Position(1, 0)) == '.'   # bP captured
    assert game.board.get_token(Position(0, 0)) == '.'

def test_rook_captures_two_enemies_on_path():
    # wR at col=0, bP at col=1, bP at col=2, empty at col=3
    game = _make([['wR', 'bP', 'bP', '.']])
    game.click(50, 50)
    game.click(350, 50)
    game.wait(2000)
    assert game.board.get_token(Position(3, 0)) == 'wR'
    assert game.board.get_token(Position(1, 0)) == '.'
    assert game.board.get_token(Position(2, 0)) == '.'

def test_black_rook_captures_white_mid_path():
    game = _make([['.', 'wP', '.', 'bR']])
    game.click(350, 50)
    game.click(50, 50)
    game.wait(2000)
    assert game.board.get_token(Position(0, 0)) == 'bR'
    assert game.board.get_token(Position(1, 0)) == '.'


# ─────────────────────────────────────────────
# Integration: same-slot arrival priority
# ─────────────────────────────────────────────

def test_earlier_departure_wins_same_target_square():
    # wR departs t=0 to col=2, bR departs t=0 to col=2 — wR clicked first, wins
    # Use non-overlapping columns so column-conflict doesn't block bR
    # wR: col=0 → col=2 (cols 0,1,2), bR: col=4 → col=2 (cols 2,3,4) — overlap at col=2
    # column conflict will block the second move, so use a wait between clicks
    game = _make([['wR', '.', '.', '.', 'bR']])
    game.click(50, 50)
    game.click(250, 50)    # wR → col=2, departs t=0
    game.wait(0)           # flush column tracking not needed, just separate selection
    game.click(450, 50)
    game.click(250, 50)    # bR → col=2, departs t=0 — same target
    game.wait(3000)
    # wR departed first, wins col=2; bR is discarded
    winner = game.board.get_token(Position(2, 0))
    assert winner == 'wR'

def test_two_pieces_arrive_at_different_squares_both_land():
    # wR col=0→col=1, bR col=4→col=3 — no conflict, both land
    game = _make([['wR', '.', '.', '.', 'bR']])
    game.click(50, 50)
    game.click(150, 50)
    game.click(450, 50)
    game.click(350, 50)
    game.wait(1000)
    assert game.board.get_token(Position(1, 0)) == 'wR'
    assert game.board.get_token(Position(3, 0)) == 'bR'
