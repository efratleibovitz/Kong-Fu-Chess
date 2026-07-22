"""tests/unit/test_rooms.py"""

import asyncio
import json

import pytest

import server.core.game_logger as game_logger
from server.core.protocol import Role
from server.game.session import GameSession
from server.game.rooms import create_room
from server.game.connection import Connection


class FakeWebSocket:
    """Doubles as both a raw websocket and a Connection: assign_color
    stores whatever object it's given as the "connection", and broadcast()
    calls .send_raw() on it - real Connection objects provide both from
    a wrapped websocket, so this fake just implements both directly."""

    def __init__(self):
        self.sent = []

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def send_raw(self, payload):
        self.sent.append(json.loads(payload))

    async def close(self):
        pass


@pytest.fixture(autouse=True)
def redirect_log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(game_logger, "LOG_DIR", str(tmp_path))


class TestCreateRoom:
    def test_create_room_returns_working_session(self):
        room_id = create_room()

        from server.game.session import get_session
        session = get_session(room_id)

        assert session is not None
        assert session.room_id == room_id
        assert session.allow_viewers is True


class TestRoomAssignment:
    def test_first_two_distinct_joiners_become_white_and_black(self):
        session = GameSession(allow_viewers=True)
        conn_a, conn_b = FakeWebSocket(), FakeWebSocket()

        role_a = session.assign_color(conn_a, user_id=1)
        role_b = session.assign_color(conn_b, user_id=2)

        assert role_a is Role.WHITE
        assert role_b is Role.BLACK
        assert session.white_user_id == 1
        assert session.black_user_id == 2

    def test_third_distinct_joiner_becomes_viewer(self):
        session = GameSession(allow_viewers=True)
        conn_a, conn_b, conn_c = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()

        session.assign_color(conn_a, user_id=1)
        session.assign_color(conn_b, user_id=2)
        role_c = session.assign_color(conn_c, user_id=3)

        assert role_c is Role.VIEWER
        assert conn_c in session.viewers
        assert conn_c not in session.connections.values()

    def test_viewer_disconnect_removes_from_viewers_without_forfeit(self):
        session = GameSession(allow_viewers=True)
        conn_a, conn_b, conn_c = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()
        session.assign_color(conn_a, user_id=1)
        session.assign_color(conn_b, user_id=2)
        session.assign_color(conn_c, user_id=3)
        session._game_started = True

        session.on_disconnect(conn_c)

        assert conn_c not in session.viewers
        assert session._forfeit_tasks == {}

    def test_matchmaking_style_session_still_rejects_third_connection(self):
        """Regression guard: allow_viewers=False (matchmaking default)
        must keep rejecting an unrelated/duplicate connection, not turn it
        into a viewer."""
        session = GameSession(white_user_id=1, black_user_id=2)
        conn_a, conn_b, conn_c = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()

        assert session.assign_color(conn_a, user_id=1) is Role.WHITE
        assert session.assign_color(conn_b, user_id=2) is Role.BLACK
        assert session.assign_color(conn_c, user_id=3) is None
        assert session.viewers == []


class TestViewerBroadcast:
    def test_broadcast_reaches_viewers(self):
        async def run():
            session = GameSession(allow_viewers=True)
            conn_a, conn_b, conn_c = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()
            session.assign_color(conn_a, user_id=1)
            session.assign_color(conn_b, user_id=2)
            session.assign_color(conn_c, user_id=3)

            await session.broadcast({"type": "state", "data": {}})

            assert conn_c.sent == [{"type": "state", "data": {}}]

        asyncio.run(run())


class MockSession:
    def __init__(self):
        self.engine = None


class TestViewerBlockedFromMoves:
    def test_handle_message_is_noop_for_viewer(self):
        async def run():
            ws = FakeWebSocket()
            session = MockSession()
            connection = Connection(ws, session, user_id=1)
            connection.is_viewer = True

            await connection._handle_message(json.dumps({"type": "click", "col": 0, "row": 0}))

            assert session.engine is None  # never touched

        asyncio.run(run())
