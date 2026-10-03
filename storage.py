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
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                plan TEXT DEFAULT 'free',
                plan_expires DATE,
                usage_month TEXT DEFAULT '',
                usage_text INTEGER DEFAULT 0,
                usage_image INTEGER DEFAULT 0,
                usage_audio INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mtype TEXT,
                prompt TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
