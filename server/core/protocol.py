"""server/core/protocol.py

Shared wire-protocol constants for the client<->server websocket messages,
plus general server configuration (host/ports). Both server/ and client/
import these instead of repeating raw string literals for message "type"
values and player colors, so a typo becomes a NameError during development
instead of a silent protocol mismatch.
"""

from dataclasses import dataclass, field
from enum import Enum

HOST = "localhost"
PORT = 8765
MATCHMAKING_PORT = 8766

COLOR_WHITE = "w"
COLOR_BLACK = "b"

class MsgType(Enum):
    """Wire-protocol "type" field values. This enum is the single source of
    truth; the MSG_TYPE_* constants below just expose `.value` so every
    existing call site (dict literals, `msg.get("type") == MSG_TYPE_X`
    comparisons) keeps working unchanged - only the definition moved from a
    bare string to an enum member, per the "missing enum" review note."""
    CLICK = "click"
    JUMP = "jump"
    RESTART = "restart"
    STATE = "state"
    WAITING = "waiting"
    START = "start"
    GAME_OVER = "game_over"
    MATCH_FOUND = "match_found"
    ERROR = "error"
    ROLE = "role"


MSG_TYPE_CLICK = MsgType.CLICK.value
MSG_TYPE_JUMP = MsgType.JUMP.value
MSG_TYPE_RESTART = MsgType.RESTART.value
MSG_TYPE_STATE = MsgType.STATE.value
MSG_TYPE_WAITING = MsgType.WAITING.value
MSG_TYPE_START = MsgType.START.value
MSG_TYPE_GAME_OVER = MsgType.GAME_OVER.value
MSG_TYPE_MATCH_FOUND = MsgType.MATCH_FOUND.value
MSG_TYPE_ERROR = MsgType.ERROR.value
MSG_TYPE_ROLE = MsgType.ROLE.value

@dataclass
class Message:
    """A websocket message: a `type` plus arbitrary named fields. Replaces
    hand-built `{"type": ..., ...}` dict literals at every send/receive
    site with one shared, typed envelope - `to_dict()` produces the exact
    same flat wire shape those literals did, so this changes nothing about
    what's actually transmitted, only how it's constructed/read in code.
    `.get()`/`__getitem__` mirror plain dict access so existing handler
    code that does `msg.get("col")`/`msg["data"]` keeps working unchanged
    whether `msg` is a `Message` or (in older/direct-construction tests) a
    bare dict."""
    type: MsgType
    fields: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": self.type.value, **self.fields}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        data = dict(data)
        return cls(type=MsgType(data.pop("type")), fields=data)

    def get(self, key, default=None):
        return self.fields.get(key, default)

    def __getitem__(self, key):
        return self.fields[key]


QUERY_ROOM_ID = "room_id"
QUERY_TOKEN = "token"
QUERY_CREATE = "create"
FLAG_TRUE = "1"
FIELD_REASON = "reason"


class Reason(Enum):
    """Values that go in an error message's "reason" field. Named here for
    the same reason MSG_TYPE_* constants exist - a typo becomes a NameError
    during development instead of a client that silently never recognizes
    a server error (or vice versa)."""
    UNAUTHORIZED = "unauthorized"
    INVALID_ROOM = "invalid_room"
    ROOM_EXISTS = "room_exists"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class Role(Enum):
    """A connection's role in a GameSession: an assigned color, or a
    read-only viewer (Stage E rooms allow a 3rd+ joiner to watch without
    playing). `.value` is what actually goes on the wire - COLOR_WHITE/
    COLOR_BLACK strings stay the single source of truth for color literals
    elsewhere in the protocol (start/match_found `"color"` fields, the
    `connections` dict keys), this enum only wraps them for the parts of
    the code that need to reason about "what role did this connection get"
    as a type instead of a bare string sentinel."""
    WHITE = COLOR_WHITE
    BLACK = COLOR_BLACK
    VIEWER = "viewer"
