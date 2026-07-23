"""tests/unit/test_network_session.py"""

from unittest.mock import MagicMock

from client.network_session import NetworkSession, FEEDBACK_DURATION_MS
from view.render_state import RenderState, PieceRenderInfo, PlayerRenderInfo
from view.constants import PieceState
from server.core.protocol import COLOR_WHITE


def _player():
    return PlayerRenderInfo(name="P", score=0, captured=[], move_history=[])


def _piece(token, col, row):
    return PieceRenderInfo(token=token, col=col, row=row, state=PieceState.IDLE, cooldown_fill=0.0, cooldown_is_long=False)


def _make_rs(pieces, selected_col=None, selected_row=None):
    return RenderState(
        num_cols=8, num_rows=8,
        pieces=pieces, selected_col=selected_col, selected_row=selected_row,
        pending_destinations=[],
        clock_ms=0, white=_player(), black=_player(),
        game_over=False, loser=None,
    )


def _make_session():
    client = MagicMock()
    client.poll.return_value = []
    session = NetworkSession(client, COLOR_WHITE)
    return session, client


def _xy(col, row):
    return col * 100 + 50, row * 100 + 50


class TestClickIsAllowed:
    def test_own_piece_is_allowed(self):
        session, _ = _make_session()
        session._rs = _make_rs([_piece("wP", 3, 4)])

        allowed, message = session._click_is_allowed(3, 4)

        assert allowed is True
        assert message is None

    def test_opponent_piece_with_nothing_selected_is_rejected_with_message(self):
        session, _ = _make_session()
        session._rs = _make_rs([_piece("bP", 3, 4)])

        allowed, message = session._click_is_allowed(3, 4)

        assert allowed is False
        assert message == "Not your piece"

    def test_opponent_piece_with_own_piece_selected_is_allowed(self):
        session, _ = _make_session()
        session._rs = _make_rs(
            [_piece("wP", 1, 1), _piece("bP", 3, 4)],
            selected_col=1, selected_row=1,
        )

        allowed, message = session._click_is_allowed(3, 4)

        assert allowed is True
        assert message is None

    def test_empty_square_with_nothing_selected_is_rejected_without_message(self):
        session, _ = _make_session()
        session._rs = _make_rs([])

        allowed, message = session._click_is_allowed(3, 4)

        assert allowed is False
        assert message is None


class TestJumpIsAllowed:
    def test_own_piece_is_allowed(self):
        session, _ = _make_session()
        session._rs = _make_rs([_piece("wP", 3, 4)])

        allowed, message = session._jump_is_allowed(3, 4)

        assert allowed is True
        assert message is None

    def test_opponent_piece_is_rejected_with_message(self):
        session, _ = _make_session()
        session._rs = _make_rs([_piece("bP", 3, 4)])

        allowed, message = session._jump_is_allowed(3, 4)

        assert allowed is False
        assert message == "Not your piece"


class TestClickIntegration:
    def test_click_on_opponent_piece_does_not_send_and_shows_feedback(self):
        session, client = _make_session()
        session._rs = _make_rs([_piece("bP", 3, 4)])

        session.click(*_xy(3, 4))

        client.send_click.assert_not_called()
        assert session._feedback == "Not your piece"

    def test_click_on_own_piece_sends(self):
        session, client = _make_session()
        session._rs = _make_rs([_piece("wP", 3, 4)])

        session.click(*_xy(3, 4))

        client.send_click.assert_called_once_with(3, 4)


class TestFeedbackLifecycle:
    def test_show_feedback_sets_rs_message_after_wait(self):
        session, _ = _make_session()
        session._rs = _make_rs([])

        session._show_feedback("Not your piece")
        session.wait(16)

        assert session._rs.message == "Not your piece"

    def test_feedback_clears_after_duration_elapses(self):
        session, _ = _make_session()
        session._rs = _make_rs([])

        session._show_feedback("Not your piece")
        session.wait(FEEDBACK_DURATION_MS)

        assert session._feedback is None
        assert session._rs.message is None

    def test_feedback_persists_before_duration_elapses(self):
        session, _ = _make_session()
        session._rs = _make_rs([])

        session._show_feedback("Not your piece")
        session.wait(FEEDBACK_DURATION_MS - 1)

        assert session._feedback == "Not your piece"
        assert session._rs.message == "Not your piece"
