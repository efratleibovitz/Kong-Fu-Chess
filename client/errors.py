"""client/errors.py

Typed exception for a server-sent error message. Carries the actual
Reason enum (not just its string) so callers can match on it structurally,
and so a broad `except RuntimeError` doesn't also swallow unrelated bugs.
Knows how to describe itself to a human, so callers don't need a parallel
reason->text table of their own.
"""

from server.core.protocol import Reason


class ServerError(Exception):
    _MESSAGES = {
        Reason.ROOM_EXISTS: "That room name is already taken - try another.",
        Reason.INVALID_ROOM: "That room doesn't exist - check the code and try again.",
        Reason.UNAUTHORIZED: "Authorization failed - please log in again.",
        Reason.TIMEOUT: "No match found in time - please try again.",
        Reason.REJECTED: "That room is already full.",
    }

    def __init__(self, reason: Reason):
        self.reason = reason
        super().__init__(reason.value)

    @property
    def friendly_message(self) -> str:
        return self._MESSAGES.get(self.reason, f"Error: {self.reason.value}")
