"""server/game/rooms.py

Ad-hoc room creation: a second entry point into GameSession alongside
matchmaking. There is no separate join_room() - joining a room is already
exactly what server.game.connection.game_handler + GameSession.assign_color
do via get_session(room_id), so a second function would just duplicate
that path.
"""

import uuid

from server.game.session import GameSession, register_session


def create_room() -> str:
    room_id = str(uuid.uuid4())
    register_session(room_id, GameSession(allow_viewers=True))
    return room_id
