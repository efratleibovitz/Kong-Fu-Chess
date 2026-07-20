import hashlib
import os
import secrets

from server.db import init_db, create_user, get_user_by_username, get_user_by_id, update_user_elo, create_session_record, get_user_id_by_token as _db_get_token

_ITERATIONS = 100_000
_HASH_NAME = "sha256"


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode(), salt, _ITERATIONS)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":", 1)
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode(), salt, _ITERATIONS)
    return dk.hex() == dk_hex


def register(username: str, password: str) -> int:
    init_db()
    if get_user_by_username(username):
        raise ValueError(f"Username '{username}' is already taken.")
    password_hash = _hash_password(password)
    return create_user(username, password_hash)


def login(username: str, password: str) -> int | None:
    init_db()
    user = get_user_by_username(username)
    if user and _verify_password(password, user["password_hash"]):
        return user["id"]
    return None


def update_elo(winner_id: int, loser_id: int, k: int = 32) -> tuple[int, int]:
    winner = get_user_by_id(winner_id)
    loser = get_user_by_id(loser_id)

    ew = 1 / (1 + 10 ** ((loser["elo"] - winner["elo"]) / 400))
    el = 1 - ew

    new_winner_elo = round(winner["elo"] + k * (1 - ew))
    new_loser_elo = round(loser["elo"] + k * (0 - el))

    update_user_elo(winner_id, new_winner_elo)
    update_user_elo(loser_id, new_loser_elo)

    return new_winner_elo, new_loser_elo


def create_session(user_id: int) -> str:
    init_db()
    token = secrets.token_urlsafe(32)
    create_session_record(token, user_id)
    return token


def get_user_id_by_token(token: str) -> int | None:
    init_db()
    return _db_get_token(token)


def login_with_session(username: str, password: str) -> tuple[int, str] | None:
    user_id = login(username, password)
    if user_id is None:
        return None
    token = create_session(user_id)
    return user_id, token
