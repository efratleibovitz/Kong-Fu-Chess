import pytest
from unittest.mock import patch


def make_user(user_id, elo):
    return {"id": user_id, "username": f"user{user_id}", "password_hash": "", "elo": elo}


def run_elo(winner_elo, loser_elo, k=32):
    """Call update_elo with mocked DB — no real DB needed."""
    winner = make_user(1, winner_elo)
    loser = make_user(2, loser_elo)

    with patch("server.auth.get_user_by_id", side_effect=lambda uid: winner if uid == 1 else loser), \
         patch("server.auth.update_user_elo", return_value=None):
        from server.auth import update_elo
        return update_elo(1, 2, k)


class TestUpdateElo:
    def test_higher_rated_wins(self):
        new_w, new_l = run_elo(winner_elo=1400, loser_elo=1200)
        # favourite wins → small gain
        assert new_w > 1400
        assert new_l < 1200
        assert new_w - 1400 < 16  # gain is less than half K

    def test_lower_rated_wins(self):
        new_w, new_l = run_elo(winner_elo=1200, loser_elo=1400)
        # underdog wins → large gain
        assert new_w > 1200
        assert new_l < 1400
        assert new_w - 1200 > 16  # gain is more than half K

    def test_close_ratings(self):
        new_w, new_l = run_elo(winner_elo=1200, loser_elo=1200)
        # equal ratings → each moves by K/2
        assert new_w == 1216
        assert new_l == 1184
        assert (new_w - 1200) + (1200 - new_l) == 32  # zero-sum
