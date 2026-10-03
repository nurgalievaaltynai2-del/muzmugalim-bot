import os
import sqlite3
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from config import TARIFFS

_DB_PATH = os.getenv("DB_PATH", "muzmugalim.db")
_HISTORY_LIMIT = 10
_FAVORITES_LIMIT = 20


@contextmanager
def _conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row(r) -> dict:
    return dict(r) if r else {}


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                first_name   TEXT,
                last_name    TEXT,
                plan         TEXT NOT NULL DEFAULT 'free',
                activated_at TEXT,
                expires_at   TEXT,
                reset_month  TEXT NOT NULL DEFAULT '',
                text_used    INTEGER NOT NULL DEFAULT 0,
                poster_used  INTEGER NOT NULL DEFAULT 0,
                music_used   INTEGER NOT NULL DEFAULT 0,
                text_total   INTEGER NOT NULL DEFAULT 0,
                poster_total INTEGER NOT NULL DEFAULT 0,
                music_total  INTEGER NOT NULL DEFAULT 0,
                first_seen   TEXT NOT NULL,
                last_seen    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                section       TEXT NOT NULL,
                material_name TEXT NOT NULL,
                material_type TEXT NOT NULL,
                topic         TEXT NOT NULL,
                result        TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                section       TEXT NOT NULL,
                material_name TEXT NOT NULL,
                material_type TEXT NOT NULL,
                topic         TEXT NOT NULL,
                result        TEXT,
                created_at    TEXT NOT NULL
            )
        """)


def _month_key() -> str:
    return date.today().replace(day=1).isoformat()


def _now() -> str:
    return datetime.utcnow().isoformat()


def _reset_if_new_month(conn, user_id: int):
    mk = _month_key()
    row = conn.execute("SELECT reset_month FROM users WHERE user_id=?", (user_id,)).fetchone()
    if row and row["reset_month"] != mk:
        conn.execute(
            "UPDATE users SET text_used=0, poster_used=0, music_used=0, reset_month=? WHERE user_id=?",
            (mk, user_id),
        )


def ensure_user(tg_user) -> dict:
    now = _now()
    mk = _month_key()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (tg_user.id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, plan, reset_month, first_seen, last_seen) VALUES (?, ?, ?, ?, 'free', ?, ?, ?)",
                (tg_user.id, tg_user.username, tg_user.first_name, getattr(tg_user, "last_name", None), mk, now, now),
            )
        else:
            conn.execute

               
