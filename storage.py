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
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "user_id INTEGER PRIMARY KEY,"
            "username TEXT,"
            "first_name TEXT,"
            "last_name TEXT,"
            "plan TEXT DEFAULT 'free',"
            "plan_expires DATE,"
            "usage_month TEXT DEFAULT '',"
            "usage_text INTEGER DEFAULT 0,"
            "usage_image INTEGER DEFAULT 0,"
            "usage_audio INTEGER DEFAULT 0,"
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS history ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "user_id INTEGER,"
            "mtype TEXT,"
            "prompt TEXT,"
            "result TEXT,"
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS favorites ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "user_id INTEGER,"
            "hist_id INTEGER,"
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )


def _month_key():
    return date.today().strftime("%Y-%m")


def _now():
    return datetime.now()


def _reset_if_new_month(conn, user_id):
    cur = conn.execute("SELECT usage_month FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row and row["usage_month"] != _month_key():
        conn.execute(
            "UPDATE users SET usage_month=?, usage_text=0, usage_image=0, usage_audio=0 WHERE user_id=?",
            (_month_key(), user_id)
        )


def ensure_user(tg_user):
    with _conn() as conn:
        cur = conn.execute("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,))
        if not cur.fetchone():
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, usage_month) VALUES (?,?,?,?,?)",
                (tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name, _month_key())
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, first_name=?, last_name=? WHERE user_id=?",
                (tg_user.username, tg_user.first_name, tg_user.last_name, tg_user.id)
            )


def check_quota(user_id, mtype):
    with _conn() as conn:
        _reset_if_new_month(conn, user_id)
        cur = conn.execute(
            "SELECT plan, plan_expires, usage_text, usage_image, usage_audio FROM users WHERE user_id=?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return False
        plan = row["plan"]
        if plan != "free" and row["plan_expires"]:
            if date.today() > date.fromisoformat(str(row["plan_expires"])):
                plan = "free"
        limits = TARIFFS.get(plan, TARIFFS["free"])
        used = row["usage_" + mtype]
        limit = limits.get(mtype, 0)
        return used < limit


def get_remaining(user_id, mtype):
    with _conn() as conn:
        _reset_if_new_month(conn, user_id)
        cur = conn.execute(
            "SELECT plan, plan_expires, usage_text, usage_image, usage_audio FROM users WHERE user_id=?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return 0
        plan = row["plan"]
        if plan != "free" and row["plan_expires"]:
            if date.today() > date.fromisoformat(str(row["plan_expires"])):
                plan = "free"
        limits = TARIFFS.
get(plan, TARIFFS["free"])
        used = row["usage_" + mtype]
        limit = limits.get(mtype, 0)
        return max(0, limit - used)


def record_usage(user_id, mtype):
    with _conn() as conn:
        _reset_if_new_month(conn, user_id)
        conn.execute(
            "UPDATE users SET usage_" + mtype + "=usage_" + mtype + "+1 WHERE user_id=?",
            (user_id,)
        )


def save_history(user_id, mtype, prompt, result):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO history (user_id, mtype, prompt, result) VALUES (?,?,?,?)",
            (user_id, mtype, prompt, result)
        )
        cur = conn.execute(
            "SELECT id FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT -1 OFFSET ?",
            (user_id, _HISTORY_LIMIT)
        )
        old = [r["id"] for r in cur.fetchall()]
        if old:
            placeholders = ",".join("?" * len(old))
            conn.execute("DELETE FROM history WHERE id IN (" + placeholders + ")", old)


def get_history(user_id):
    with _conn() as conn:
        cur = conn.execute(
            "SELECT id, mtype, prompt, created_at FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, _HISTORY_LIMIT)
        )
        return [_row(r) for r in cur.fetchall()]


def get_history_item(hist_id, user_id):
    with _conn() as conn:
        cur = conn.execute(
            "SELECT * FROM history WHERE id=? AND user_id=?",
            (hist_id, user_id)
        )
        return _row(cur.fetchone())


def add_favorite(user_id, hist_id):
    with _conn() as conn:
        cur = conn.execute(
            "SELECT id FROM favorites WHERE user_id=? AND hist_id=?",
            (user_id, hist_id)
        )
        if cur.fetchone():
            return False
        cur2 = conn.execute(
            "SELECT COUNT(*) as c FROM favorites WHERE user_id=?",
            (user_id,)
        )
        if cur2.fetchone()["c"] >= _FAVORITES_LIMIT:
            return False
        conn.execute(
            "INSERT INTO favorites (user_id, hist_id) VALUES (?,?)",
            (user_id, hist_id)
        )
        return True


def remove_favorite(user_id, fav_id):
    with _conn() as conn:
        conn.execute(
            "DELETE FROM favorites WHERE id=? AND user_id=?",
            (fav_id, user_id)
        )


def get_favorites(user_id):
    with _conn() as conn:
        cur = conn.execute(
            "SELECT f.id, h.mtype, h.prompt, f.created_at"
            " FROM favorites f JOIN history h ON f.hist_id=h.id"
            " WHERE f.user_id=? ORDER BY f.created_at DESC",
            (user_id,)
        )
        return [_row(r) for r in cur.fetchall()]


def get_favorite_item(fav_id, user_id):
    with _conn() as conn:
        cur = conn.execute(
            "SELECT h.* FROM favorites f JOIN history h ON f.hist_id=h.id"
            " WHERE f.id=? AND f.user_id=?",
            (fav_id, user_id)
        )
        return _row(cur.fetchone())


def activate_plan(user_id, plan, days=30):
    expires = date.today() + timedelta(days=days)
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET plan=?, plan_expires=? WHERE user_id=?",
            (plan, expires.isoformat(), user_id)
        )


def get_expiring_users(days=3):
    target = date.today() + timedelta(days=days)
    with _conn() as conn:
        cur = conn.execute(
            "SELECT user_id, first_name, plan, plan_expires FROM users WHERE plan_expires=?",
            (target.isoformat(),)
        )
        return [_row(r) for r in cur.fetchall()]


def downgrade_expired_users():
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET plan='free' WHERE plan_expires < ? AND plan != 'free'",
            (date.today().isoformat(),)
        )


def get_stats():
    with _conn() as conn:
        cur = conn.execute("SELECT COUNT(*) as total FROM users")
        total = cur.fetchone()["total"]
        cur2 = conn.execute("SELECT COUNT(*) as paid FROM users WHERE plan != 'free'")
        paid = cur2.fetchone()["paid"]
        cur3 = conn.
execute("SELECT SUM(usage_text+usage_image+usage_audio) as reqs FROM users")
        reqs = cur3.fetchone()["reqs"] or 0
        return {"total_users": total, "paid_users": paid, "total_requests": reqs}


def get_all_users(limit=20):
    with _conn() as conn:
        cur = conn.execute(
            "SELECT user_id, username, first_name, plan, plan_expires,"
            " usage_text, usage_image, usage_audio"
            " FROM users ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [_row(r) for r in cur.fetchall()]


def get_users_for_broadcast(plan_filter="all"):
    with _conn() as conn:
        if plan_filter == "all":
            cur = conn.execute("SELECT user_id FROM users")
        else:
            cur = conn.execute(
                "SELECT user_id FROM users WHERE plan=?",
                (plan_filter,)
            )
        return [r["user_id"] for r in cur.fetchall()]
