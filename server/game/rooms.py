"""server/game/rooms.py

Ad-hoc room creation: a second entry point into GameSession alongside
matchmaking. There is no separate join_room() - joining a room is already
exactly what server.game.connection.game_handler + GameSession.assign_color
do via get_session(room_id), so a second function would just duplicate
that path.
"""

import uuid

from server.game.session import GameSession, register_session


def create_room(room_id: str | None = None) -> str:
    """room_id lets a caller choose a custom, human-readable room code
    (e.g. "efrat_room") instead of a random one. Collision checking against
    an already-registered name lives in game_handler, the only caller that
    knows whether this is a fresh create vs. a name reuse - create_room
    itself just registers whatever id it's given."""
    if room_id is None:
        room_id = str(uuid.uuid4())
    register_session(room_id, GameSession(allow_viewers=True))
    return room_id
