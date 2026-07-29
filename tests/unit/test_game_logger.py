"""tests/unit/test_game_logger.py"""

import logging
import os

import pytest

import server.core.game_logger as game_logger
from server.core.protocol import Role
from server.core.game_logger import get_room_logger, log_action


@pytest.fixture(autouse=True)
def redirect_log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(game_logger, "LOG_DIR", str(tmp_path))
    return tmp_path


def _read_log(tmp_path, room_id):
    logger = get_room_logger(room_id)
    for handler in logger.handlers:
        handler.flush()
    with open(os.path.join(str(tmp_path), f"{room_id}.log")) as f:
        return f.read()


class TestGetRoomLogger:
    def test_creates_file_only_logger_no_console_handler(self, tmp_path):
        logger = get_room_logger("room-1")

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)
        assert logger.propagate is False
        assert os.path.exists(os.path.join(str(tmp_path), "room-1.log"))

    def test_reuses_same_handler_on_repeated_calls(self):
        logger_a = get_room_logger("room-2")
        logger_b = get_room_logger("room-2")

        assert logger_a is logger_b
        assert len(logger_a.handlers) == 1


class TestLogAction:
    def test_line_contains_username_id_role_action_comment(self, tmp_path):
        log_action("room-3", 7, "alice", Role.WHITE, "click", "col=3, row=4")

        content = _read_log(tmp_path, "room-3")
        assert "room-3" in content
        assert "alice" in content
        assert "#7" in content
        assert "White" in content
        assert "click" in content
        assert "col=3, row=4" in content

    def test_accepts_raw_role_string(self, tmp_path):
        log_action("room-4", 9, "bob", "viewer", "connect")

        content = _read_log(tmp_path, "room-4")
        assert "bob" in content
        assert "Viewer" in content
        assert "connect" in content

    def test_no_comment_omits_trailing_separator(self, tmp_path):
        log_action("room-5", 1, "carol", Role.BLACK, "disconnect")

        content = _read_log(tmp_path, "room-5")
        assert content.strip().endswith("disconnect")

    def test_no_generic_event_bus_subscription_api_remains(self):
        """Regression guard: logging moved from subscribing to every
        EventBus event (anonymous, no actor) to explicit log_action calls
        at the sites that know who's acting. The old API must be gone."""
        assert not hasattr(game_logger, "attach_event_logger")
        assert not hasattr(game_logger, "KNOWN_EVENTS")
