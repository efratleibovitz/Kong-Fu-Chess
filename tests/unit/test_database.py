"""tests/unit/test_database.py"""

import uuid

from server.core.database import init_db, create_user, get_player_record, PlayerRecord


class TestGetPlayerRecord:
    def test_returns_player_record_with_real_data(self):
        init_db()
        username = f"test_player_record_{uuid.uuid4().hex[:8]}"
        user_id = create_user(username, "irrelevant_hash")

        record = get_player_record(user_id)

        assert isinstance(record, PlayerRecord)
        assert record.user_id == user_id
        assert record.username == username
        assert record.elo == 1200  # schema default

    def test_returns_none_for_unknown_user(self):
        init_db()
        assert get_player_record(-1) is None
