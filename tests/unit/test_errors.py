"""tests/unit/test_errors.py"""

import pytest

from server.core.protocol import Reason
from client.errors import ServerError


class TestServerError:
    @pytest.mark.parametrize("reason", list(Reason))
    def test_every_reason_has_a_friendly_message(self, reason):
        err = ServerError(reason)
        assert isinstance(err.friendly_message, str)
        assert err.friendly_message != ""

    def test_reason_attribute_holds_original_enum(self):
        err = ServerError(Reason.ROOM_EXISTS)
        assert err.reason is Reason.ROOM_EXISTS

    def test_room_exists_message_mentions_taken(self):
        err = ServerError(Reason.ROOM_EXISTS)
        assert "taken" in err.friendly_message.lower()

    def test_invalid_room_message_mentions_doesnt_exist(self):
        err = ServerError(Reason.INVALID_ROOM)
        assert "doesn't exist" in err.friendly_message.lower()

    def test_str_of_exception_is_the_wire_value(self):
        err = ServerError(Reason.TIMEOUT)
        assert str(err) == "timeout"
