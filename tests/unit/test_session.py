import pytest
from unittest.mock import patch, MagicMock


class TestSession:
    def test_login_with_session_returns_user_id_and_token(self):
        with patch("server.auth.service.login", return_value=42), \
             patch("server.auth.service.create_session", return_value="valid_token"):
            from server.auth.service import login_with_session
            result = login_with_session("alice", "password")
            assert result == (42, "valid_token")

    def test_get_user_id_by_token_returns_correct_user_id(self):
        with patch("server.auth.service._db_get_token", return_value=42):
            from server.auth.service import get_user_id_by_token
            assert get_user_id_by_token("valid_token") == 42

    def test_get_user_id_by_token_returns_none_for_forged_token(self):
        with patch("server.auth.service._db_get_token", return_value=None):
            from server.auth.service import get_user_id_by_token
            assert get_user_id_by_token("forged_token") is None
