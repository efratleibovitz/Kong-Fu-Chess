"""tests/unit/test_rooms.py"""

import asyncio
import json
import types

import pytest

import server.core.game_logger as game_logger
from server.core.protocol import Role, COLOR_WHITE, COLOR_BLACK, Message, MsgType
from server.game.session import GameSession
from server.game.rooms import create_room
from server.game.connection import Connection, game_handler


class FakeWebSocket:
    """Doubles as both a raw websocket and a Connection: assign_color
    stores whatever object it's given as the "connection", and broadcast()
    calls .send_raw() on it - real Connection objects provide both from
    a wrapped websocket, so this fake just implements both directly.
    game_handler tests also need `.request.path` (for urlparse) and async
    iteration (Connection.run()'s `async for raw in self.client_socket` - an
    empty/closed stream, since these tests only care about game_handler's
    routing, not live gameplay)."""

    def __init__(self, path=""):
        self.sent = []
        self.request = types.SimpleNamespace(path=path)

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def send_raw(self, payload):
        self.sent.append(json.loads(payload))

    async def close(self):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


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

    def test_create_room_with_custom_name_uses_it(self):
        room_id = create_room("efrat_room_unit_test")

        from server.game.session import get_session

        assert room_id == "efrat_room_unit_test"
        assert get_session("efrat_room_unit_test") is not None


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

            await session.broadcast(Message(MsgType.STATE, {"data": {}}))

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


class TestConnectionLogging:
    def test_click_logs_room_user_role_and_comment(self, monkeypatch):
        logged = []
        monkeypatch.setattr(
            "server.game.connection.log_action",
            lambda room_id, user_id, username, role, action, comment="": logged.append(
                (room_id, user_id, username, role, action, comment)
            ),
        )
        session = MockSession()
        session.room_id = "room-x"
        session.engine = types.SimpleNamespace(click_cell=lambda col, row, color: None)
        connection = Connection(FakeWebSocket(), session, user_id=7)
        connection.color = COLOR_WHITE
        connection._role = Role.WHITE
        connection.username = "alice"
        monkeypatch.setattr(connection, "_click_is_allowed", lambda col, row: True)

        connection._handle_click({"col": 3, "row": 4})

        assert logged == [("room-x", 7, "alice", Role.WHITE, "click", "col=3, row=4")]

    def test_disallowed_click_is_not_logged(self, monkeypatch):
        logged = []
        monkeypatch.setattr(
            "server.game.connection.log_action",
            lambda *a, **k: logged.append((a, k)),
        )
        session = MockSession()
        session.room_id = "room-y"
        session.engine = types.SimpleNamespace(click_cell=lambda col, row, color: None)
        connection = Connection(FakeWebSocket(), session, user_id=7)
        connection.color = COLOR_WHITE
        connection._role = Role.WHITE
        connection.username = "alice"
        monkeypatch.setattr(connection, "_click_is_allowed", lambda col, row: False)

        connection._handle_click({"col": 3, "row": 4})

        assert logged == []


class TestGameHandlerRoomCreation:
    @pytest.fixture(autouse=True)
    def stub_auth(self, monkeypatch):
        monkeypatch.setattr("server.game.connection.get_user_id_by_token", lambda token: 1)
        monkeypatch.setattr("server.game.connection.get_user_by_id", lambda uid: {"username": "alice"})

    def test_create_with_no_name_assigns_fresh_room(self):
        async def run():
            ws = FakeWebSocket(path="/?create=1&token=t")
            await game_handler(ws)

            waiting = next(m for m in ws.sent if m["type"] == "waiting")
            assert waiting["room_id"]

            from server.game.session import get_session
            assert get_session(waiting["room_id"]) is not None

        asyncio.run(run())

    def test_create_with_free_name_uses_it(self):
        async def run():
            ws = FakeWebSocket(path="/?create=1&room_id=my_custom_room_abc&token=t")
            await game_handler(ws)

            waiting = next(m for m in ws.sent if m["type"] == "waiting")
            assert waiting["room_id"] == "my_custom_room_abc"

        asyncio.run(run())

    def test_create_with_taken_name_errors_room_exists(self):
        async def run():
            create_room("already_taken_room")
            ws = FakeWebSocket(path="/?create=1&room_id=already_taken_room&token=t")

            await game_handler(ws)

            assert ws.sent == [{"type": "error", "reason": "room_exists"}]

        asyncio.run(run())

    def test_join_unknown_room_errors_invalid_room(self):
        async def run():
            ws = FakeWebSocket(path="/?room_id=does_not_exist_room&token=t")

            await game_handler(ws)

            assert ws.sent == [{"type": "error", "reason": "invalid_room"}]

        asyncio.run(run())

    def test_join_without_room_id_errors_invalid_room(self):
        async def run():
            ws = FakeWebSocket(path="/?token=t")

            await game_handler(ws)

            assert ws.sent == [{"type": "error", "reason": "invalid_room"}]

        asyncio.run(run())


class TestRoomIsolation:
    """Todo-list item: 'Take care of isolation between the rooms' - two
    rooms must never share state, and acting in one must never be visible
    in another."""

    def test_rooms_have_independent_board_and_piece_objects(self):
        from server.game.session import get_session
        from core.model.position import Position

        room_a = create_room()
        room_b = create_room()
        session_a = get_session(room_a)
        session_b = get_session(room_b)

        assert session_a is not session_b
        assert session_a.state is not session_b.state
        assert session_a.state.board is not session_b.state.board
        assert session_a.state.board.get_piece(Position(0, 6)) is not session_b.state.board.get_piece(Position(0, 6))

    def test_selecting_a_piece_in_one_room_does_not_select_in_another(self):
        async def run():
            from server.game.session import get_session

            room_a = create_room()
            room_b = create_room()
            session_a = get_session(room_a)
            session_b = get_session(room_b)

            session_a.engine.click_cell(0, 6, COLOR_WHITE)  # select white pawn in room A only

            assert session_a.state.selected_by_color['w'] is not None
            assert session_b.state.selected_by_color['w'] is None

        asyncio.run(run())

    def test_moving_a_piece_in_one_room_leaves_the_other_rooms_board_untouched(self):
        async def run():
            from server.game.session import get_session
            from core.model.position import Position

            room_a = create_room()
            room_b = create_room()
            session_a = get_session(room_a)
            session_b = get_session(room_b)

            session_a.engine.click_cell(0, 6, COLOR_WHITE)
            session_a.engine.click_cell(0, 5, COLOR_WHITE)
            session_a.engine.wait(1000)

            assert session_a.state.board.get_token(Position(0, 5)) == 'wP'
            assert session_b.state.board.get_token(Position(0, 6)) == 'wP'
            assert session_b.state.board.get_token(Position(0, 5)) == '.'

        asyncio.run(run())

    def test_broadcast_in_one_room_never_reaches_another_rooms_connections(self):
        async def run():
            from server.game.session import get_session

            room_a = create_room()
            room_b = create_room()
            session_a = get_session(room_a)
            session_b = get_session(room_b)

            conn_a = FakeWebSocket()
            conn_b = FakeWebSocket()
            session_a.assign_color(conn_a, user_id=1)
            session_b.assign_color(conn_b, user_id=2)

            await session_a.broadcast(Message(MsgType.STATE, {"data": {}}))

            assert conn_a.sent == [{"type": "state", "data": {}}]
            assert conn_b.sent == []

        asyncio.run(run())


class TestPerColorSelection:
    """Reviewer-flagged bug: selected_position was a single shared field,
    so one player's click could be misread as acting on the other
    player's selection. click_cell/jump_cell now take an explicit color
    and operate on GameState.selected_by_color[color] only."""

    def test_selecting_white_does_not_touch_black_slot(self):
        async def run():
            session = GameSession(allow_viewers=True)
            from core.model.position import Position

            session.engine.click_cell(0, 6, COLOR_WHITE)

            assert session.state.selected_by_color['w'] == Position(0, 6)
            assert session.state.selected_by_color['b'] is None

        asyncio.run(run())

    def test_black_clicking_own_piece_does_not_touch_or_use_whites_selection(self):
        """The exact reviewer scenario: White selects piece A, then Black
        clicks Black's own piece B (a perfectly legal click). Black's
        click must select B for Black - it must never be interpreted as
        an attempt to move/capture with White's already-selected piece."""
        async def run():
            session = GameSession(allow_viewers=True)
            from core.model.position import Position

            session.engine.click_cell(0, 6, COLOR_WHITE)  # White selects pawn A
            session.engine.click_cell(0, 1, COLOR_BLACK)  # Black clicks own pawn B

            assert session.state.selected_by_color['w'] == Position(0, 6)  # A untouched
            assert session.state.selected_by_color['b'] == Position(0, 1)  # B selected for Black
            assert session.state.pending_moves == []  # no move/capture was scheduled
            assert session.state.board.get_token(Position(0, 6)) == 'wP'  # A never moved
            assert session.state.board.get_token(Position(0, 1)) == 'bP'  # B never captured

        asyncio.run(run())

    def test_black_cannot_select_a_white_piece(self):
        async def run():
            session = GameSession(allow_viewers=True)

            session.engine.click_cell(0, 6, COLOR_BLACK)  # Black clicks a white piece

            assert session.state.selected_by_color['b'] is None

        asyncio.run(run())

    def test_jump_cell_requires_matching_color(self):
        async def run():
            session = GameSession(allow_viewers=True)

            session.engine.jump_cell(0, 6, COLOR_BLACK)  # Black tries to jump White's pawn
            assert session.state.pending_jumps == []

            session.engine.jump_cell(0, 6, COLOR_WHITE)  # White jumps its own pawn
            assert len(session.state.pending_jumps) == 1

        asyncio.run(run())
