"""server/core/game_logger.py

Per-room, file-only action log: one readable line per real action (who did
it, in what room, in what role, and an optional plain-text comment) - not a
generic dump of model EventBus events, which don't carry an actor and would
either be empty or (via the client's message log) balloon into a full board
printout on every state broadcast. Callers that actually know who's acting
- server.game.connection.Connection and server.game.session.GameSession -
call log_action directly.
"""

import logging
import os

from server.core.protocol import Role

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")

_ROLE_LABELS = {
    Role.WHITE.value: "White",
    Role.BLACK.value: "Black",
    Role.VIEWER.value: "Viewer",
}


def _role_label(role) -> str:
    value = role.value if isinstance(role, Role) else role
    return _ROLE_LABELS.get(value, str(value))


def get_room_logger(room_id: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(f"server.game.{room_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.FileHandler(os.path.join(LOG_DIR, f"{room_id}.log"))
        handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        logger.addHandler(handler)
    return logger


def log_action(room_id: str, user_id: int, username: str, role, action: str, comment: str = "") -> None:
    logger = get_room_logger(room_id)
    line = f"room={room_id} | {username} #{user_id} ({_role_label(role)}) | {action}"
    if comment:
        line += f" | {comment}"
    logger.info(line)
