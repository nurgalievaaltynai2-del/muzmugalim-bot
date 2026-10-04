import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.getenv("DB_PATH", "muzmugalim.db")

TARIFFS = {
    "free": {"ai_requests": 10, "pdf_exports": 2, "history_days": 7},
    "basic": {"ai_requests": 100, "pdf_exports": 20, "history_days": 30},
    "pro": {"ai_requests": 500, "pdf_exports": 100, "history_days": 90},
}

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            plan TEXT DEFAULT 'free',
            plan_expires TEXT,
            ai_used INTEGER DEFAULT 0,
            pdf_used INTEGER DEFAULT 0,
            reset_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()

def ensure_user(user_id, username=None):
    with get_conn() as conn:
        conn.execute("""INSERT OR IGNORE INTO users (user_id, username, reset_date)
            VALUES (?, ?, ?)""", (user_id, username, datetime.now().date().isoformat()))
        if username:
            conn.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
        conn.commit()

def _maybe_reset(conn, user_id):
    row = conn.execute("SELECT reset_date FROM users WHERE user_id=?", (user_id,)).fetchone()
    if row:
        reset = row[0]
        if reset != datetime.now().date().isoformat():
            conn.execute("UPDATE users SET ai_used=0, pdf_used=0, reset_date=? WHERE user_id=?",
                (datetime.now().date().isoformat(), user_id))
            conn.commit()

def check_quota(user_id, quota_type):
    with get_conn() as conn:
        _maybe_reset(conn, user_id)
        row = conn.execute("SELECT plan, ai_used, pdf_used FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return False
        plan, ai_used, pdf_used = row
        limits = TARIFFS.get(plan, TARIFFS["free"])
        if quota_type == "ai":
            return ai_used < limits["ai_requests"]
        elif quota_type == "pdf":
            return pdf_used < limits["pdf_exports"]
        return False

def get_remaining(user_id, quota_type):
    with get_conn() as conn:
        _maybe_reset(conn, user_id)
        row = conn.execute("SELECT plan, ai_used, pdf_used FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return 0
        plan, ai_used, pdf_used = row
        limits = TARIFFS.get(plan, TARIFFS["free"])
        if quota_type == "ai":
            return max(0, limits["ai_requests"] - ai_used)
        elif quota_type == "pdf":
            return max(0, limits["pdf_exports"] - pdf_used)
        return 0

def record_usage(user_id, quota_type):
    with get_conn() as conn:
        if quota_type == "ai":
            conn.execute("UPDATE users SET ai_used=ai_used+1 WHERE user_id=?", (user_id,))
        elif quota_type == "pdf":
            conn.execute("UPDATE users SET pdf_used=pdf_used+1 WHERE user_id=?", (user_id,))
        conn.commit()

def save_history(user_id, role, content):
    with get_conn() as conn:
        conn.execute("INSERT INTO history (user_id, role, content) VALUES (?,?,?)",
            (user_id, role, content))
        conn.commit()

def get_history(user_id, limit=20):
    with get_conn() as conn:
        rows = conn.execute("""SELECT role, content FROM history
            WHERE user_id=? ORDER BY created_at DESC LIMIT ?""", (user_id, limit)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def add_favorite(user_id, content):
    with get_conn() as conn:
        conn.execute("INSERT INTO favorites (user_id, content) VALUES (?,?)", (user_id, content))
        conn.commit()

def remove_favorite(user_id, fav_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM favorites WHERE id=? AND user_id=?", (fav_id, user_id))
        conn.commit()

def get_favorites(user_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT id, content FROM favorites WHERE user_id=?", (user_id,)).fetchall()
        return [{"id": r[0], "content": r[1]} for r in rows]

def activate_plan(user_id, plan, days=30):
    expires = (datetime.now() + timedelta(days=days)).date().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE users SET plan=?, plan_expires=? WHERE user_id=?", (plan, expires, user_id))
        conn.commit()

def get_expiring_users(days=3):
    target = (datetime.now() + timedelta(days=days)).date().isoformat()
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE plan_expires=?", (target,)).fetchall()
        return [r[0] for r in rows]

def downgrade_expired_users():
    today = datetime.now().date().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE users SET plan='free', plan_expires=NULL WHERE plan_expires < ? AND plan != 'free'", (today,))
        conn.commit()

def get_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        by_plan = conn.execute("SELECT plan, COUNT(*) FROM users GROUP BY plan").fetchall()
        return {"total": total, "by_plan": dict(by_plan)}

def get_all_users():
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r[0] for r in rows]

def get_users_for_broadcast():
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r[0] for r in rows]
