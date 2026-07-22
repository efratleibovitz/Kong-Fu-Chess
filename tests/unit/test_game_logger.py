"""tests/unit/test_game_logger.py"""

import os

import pytest

import server.core.game_logger as game_logger
from model.event_bus import EventBus
from server.core.game_logger import attach_event_logger, KNOWN_EVENTS


@pytest.fixture(autouse=True)
def redirect_log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(game_logger, "LOG_DIR", str(tmp_path))
    return tmp_path


class TestAttachEventLogger:
    def test_subscribes_to_all_known_events(self):
        events = EventBus()

        attach_event_logger(events, "room-1")

        for event_name in KNOWN_EVENTS:
            assert len(events._subscribers[event_name]) == 1

    def test_emitting_event_writes_log_line(self, tmp_path):
        events = EventBus()
        logger = attach_event_logger(events, "room-2")

        events.emit("piece_settled")
        for handler in logger.handlers:
            handler.flush()

        log_path = os.path.join(str(tmp_path), "room-2.log")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            content = f.read()
        assert "piece_settled" in content

    def test_game_over_event_logs_kwargs(self, tmp_path):
        events = EventBus()
        logger = attach_event_logger(events, "room-3")

        events.emit("game_over", loser="w")
        for handler in logger.handlers:
            handler.flush()

        log_path = os.path.join(str(tmp_path), "room-3.log")
        with open(log_path) as f:
            content = f.read()
        assert "game_over" in content
        assert "loser" in content
