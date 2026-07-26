import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chess.db")
SESSION_TTL_SECONDS = 24 * 60 * 60  # a token is valid for 24h after login


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db():
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
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        return cur.lastrowid


def get_user_by_username(username: str) -> dict | None:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def update_user_elo(user_id: int, new_elo: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET elo = ? WHERE id = ?", (new_elo, user_id)
        )


def create_session_record(token: str, user_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, datetime('now', ?))",
            (token, user_id, f"+{SESSION_TTL_SECONDS} seconds"),
        )


def get_user_id_by_token(token: str) -> int | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE token = ? AND expires_at > CURRENT_TIMESTAMP",
            (token,),
        ).fetchone()
        return row[0] if row else None
