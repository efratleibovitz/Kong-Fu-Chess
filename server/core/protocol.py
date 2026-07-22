"""server/core/protocol.py

Shared wire-protocol constants for the client<->server websocket messages,
plus general server configuration (host/ports). Both server/ and client/
import these instead of repeating raw string literals for message "type"
values and player colors, so a typo becomes a NameError during development
instead of a silent protocol mismatch.
"""

HOST = "localhost"
PORT = 8765
MATCHMAKING_PORT = 8766

COLOR_WHITE = "w"
COLOR_BLACK = "b"

MSG_TYPE_CLICK = "click"
MSG_TYPE_JUMP = "jump"
MSG_TYPE_RESTART = "restart"
MSG_TYPE_STATE = "state"
MSG_TYPE_WAITING = "waiting"
MSG_TYPE_START = "start"
MSG_TYPE_GAME_OVER = "game_over"
MSG_TYPE_MATCH_FOUND = "match_found"
MSG_TYPE_ERROR = "error"
