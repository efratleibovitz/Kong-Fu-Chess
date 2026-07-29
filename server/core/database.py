"""server/core/database.py

Two backends behind the same function signatures:
- sqlite (default): unchanged from before, used for local/dev runs and the
  existing test suite - a single process, single file is fine there.
- Postgres (when DATABASE_URL is set, as it is in docker-compose.yml): the
  actual store for the split architecture, since multiple containers
  (API Gateway, Matchmaking, every Game Server shard) hit this concurrently -
  see Server_Design.md Sec.4 Q1 for why sqlite structurally can't do that.
"""

import os
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chess.db")
DATABASE_URL = os.environ.get("DATABASE_URL")  # e.g. postgresql://user:pass@postgres:5432/chess
SESSION_TTL_SECONDS = 24 * 60 * 60  # a token is valid for 24h after login

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    import psycopg2.errors
else:
    import sqlite3


@dataclass(frozen=True)
class PlayerRecord:
    """A player's real DB identity (username, rating) - an immutable
    record (not a general mutable class): once you have one, it can't be
    changed out from under you. Sent to the client instead of a loose
    dict, once actually needed there (see GameSession._apply_player_identity)."""
    user_id: int
    username: str
    elo: int


def _connect():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)


def init_db():
    if USE_POSTGRES:
        try:
            with _connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id            SERIAL PRIMARY KEY,
                            username      TEXT    UNIQUE NOT NULL,
                            password_hash TEXT    NOT NULL,
                            elo           INTEGER NOT NULL DEFAULT 1200
                        )
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS sessions (
                            token      TEXT PRIMARY KEY,
                            user_id    INTEGER NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP
                        )
                    """)
        except psycopg2.errors.UniqueViolation:
            pass  # another service already created the tables concurrently
        return

    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                elo           INTEGER NOT NULL DEFAULT 1200
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT    PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        # migrate DBs created before expires_at existed
        columns = [row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()]
        if "expires_at" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN expires_at TIMESTAMP")


def create_user(username: str, password_hash: str) -> int:
    if USE_POSTGRES:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                    (username, password_hash),
                )
                return cur.fetchone()[0]

    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        return cur.lastrowid


def get_user_by_username(username: str) -> dict | None:
    if USE_POSTGRES:
        with _connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                return dict(row) if row else None

    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    if USE_POSTGRES:
        with _connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def update_user_elo(user_id: int, new_elo: int) -> None:
    if USE_POSTGRES:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET elo = %s WHERE id = %s", (new_elo, user_id))
        return

    with _connect() as conn:
        conn.execute(
            "UPDATE users SET elo = ? WHERE id = ?", (new_elo, user_id)
        )


def create_session_record(token: str, user_id: int) -> None:
    if USE_POSTGRES:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, NOW() + %s * INTERVAL '1 second')",
                    (token, user_id, SESSION_TTL_SECONDS),
                )
        return

    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, datetime('now', ?))",
            (token, user_id, f"+{SESSION_TTL_SECONDS} seconds"),
        )


def get_player_record(user_id: int) -> PlayerRecord | None:
    user = get_user_by_id(user_id)
    if user is None:
        return None
    return PlayerRecord(user_id=user["id"], username=user["username"], elo=user["elo"])


def get_user_id_by_token(token: str) -> int | None:
    if USE_POSTGRES:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM sessions WHERE token = %s AND expires_at > NOW()",
                    (token,),
                )
                row = cur.fetchone()
                return row[0] if row else None

    with _connect() as conn:
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE token = ? AND expires_at > CURRENT_TIMESTAMP",
            (token,),
        ).fetchone()
        return row[0] if row else None
