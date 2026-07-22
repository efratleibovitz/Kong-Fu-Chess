"""server/core/game_logger.py

Subscribes to every known model EventBus event name and writes a
structured line per event to a per-room log file - a live, readable
trail of what a GameSession did, for debugging real-time networked play.
"""

import logging
import os

KNOWN_EVENTS = ("piece_settled", "selection_changed", "restarted", "game_over")

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")


def attach_event_logger(events, room_id: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(f"server.game.{room_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.FileHandler(os.path.join(LOG_DIR, f"{room_id}.log"))
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)

    def _make_callback(event_name: str):
        def _callback(**kwargs):
            logger.info("%s %s", event_name, kwargs)
        return _callback

    for event_name in KNOWN_EVENTS:
        events.subscribe(event_name, _make_callback(event_name))

    return logger
