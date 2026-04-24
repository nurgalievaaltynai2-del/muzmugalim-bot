import sqlite3
import os
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from config import TARIFFS

DB_FILE = os.getenv("DB_FILE", "muzmugalim.db")
_HISTORY_LIMIT = 10
_FAVORITES_LIMIT = 20


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.executescript("""
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
            );

            CREATE TABLE IF NOT EXISTS history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                section       TEXT NOT NULL,
                material_name TEXT NOT NULL,
                material_type TEXT NOT NULL,
                topic         TEXT NOT NULL,
                result        TEXT,
                created_at    TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                section       TEXT NOT NULL,
                material_name TEXT NOT NULL,
                material_type TEXT NOT NULL,
                topic         TEXT NOT NULL,
                result        TEXT,
                created_at    TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)


def _month_key() -> str:
    return date.today().replace(day=1).isoformat()


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row(r) -> dict:
    return dict(r) if r else {}


def _reset_if_new_month(conn, user_id: int):
    mk = _month_key()
    row = conn.execute("SELECT reset_month FROM users WHERE user_id=?", (user_id,)).fetchone()
    if row and row["reset_month"] != mk:
        conn.execute(
            "UPDATE users SET text_used=0, poster_used=0, music_used=0, reset_month=? "
            "WHERE user_id=?",
            (mk, user_id),
        )


def ensure_user(tg_user) -> dict:
    now = _now()
    mk = _month_key()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (tg_user.id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, "
                "plan, reset_month, first_seen, last_seen) VALUES (?, ?, ?, ?, 'free', ?, ?, ?)",
                (tg_user.id, tg_user.username, tg_user.first_name,
                 getattr(tg_user, "last_name", None), mk, now, now),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, first_name=?, last_name=?, last_seen=? "
                "WHERE user_id=?",
                (tg_user.username, tg_user.first_name,
                 getattr(tg_user, "last_name", None), now, tg_user.id),
            )
            _reset_if_new_month(conn, tg_user.id)
        return _row(conn.execute("SELECT * FROM users WHERE user_id=?", (tg_user.id,)).fetchone())


def check_quota(user_id: int, mtype: str) -> tuple:
    with _conn() as conn:
        _reset_if_new_month(conn, user_id)
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return False, "Пайдаланушы табылмады"
        plan = row["plan"]
        lim = TARIFFS[plan][mtype]
        used = row[f"{mtype}_used"]

        if mtype == "text":
            if plan == "free" and lim is not None and used >= lim:
                return False, (
                    f"⚠️ Тегін лимит аяқталды ({lim} сұраныс).\n\n"
                    "Жалғастыру үшін тариф таңдаңыз 👇"
                )
        elif mtype == "poster":
            if lim == 0:
                return False, "no_poster_access"
            if lim is not None and used >= lim:
                return False, f"⚠️ Постер лимиті аяқталды ({lim}/ай).\n_Лимит постеров исчерпан._"
        elif mtype == "music":
            if lim == 0:
                return False, "no_music_access"
            if lim is not None and used >= lim:
                return False, f"⚠️ Музыка лимиті аяқталды ({lim}/ай).\n_Лимит музыки исчерпан._"
    return True, ""


def get_remaining(user_id: int, mtype: str) -> tuple:
    """Returns (used, limit). limit=None means unlimited."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return 0, 0
        plan = row["plan"]
        lim = TARIFFS[plan][mtype]
        used = row[f"{mtype}_used"]
        return used, lim


def record_usage(user_id: int, mtype: str):
    with _conn() as conn:
        conn.execute(
            f"UPDATE users SET {mtype}_used={mtype}_used+1, {mtype}_total={mtype}_total+1 "
            "WHERE user_id=?",
            (user_id,),
        )


def save_history(user_id: int, section: str, material_name: str,
                 material_type: str, topic: str, result: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO history (user_id, section, material_name, material_type, "
            "topic, result, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, section, material_name, material_type, topic, result[:4000], _now()),
        )
        hist_id = cur.lastrowid
        conn.execute(
            "DELETE FROM history WHERE user_id=? AND id NOT IN "
            "(SELECT id FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?)",
            (user_id, user_id, _HISTORY_LIMIT),
        )
        return hist_id


def get_history(user_id: int) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, _HISTORY_LIMIT),
        ).fetchall()
        return [_row(r) for r in rows]


def get_history_item(hist_id: int, user_id: int) -> dict:
    with _conn() as conn:
        return _row(conn.execute(
            "SELECT * FROM history WHERE id=? AND user_id=?", (hist_id, user_id)
        ).fetchone())


def add_favorite(user_id: int, hist_id: int) -> tuple:
    with _conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        if count >= _FAVORITES_LIMIT:
            return False, f"⚠️ Таңдаулылар толы (макс {_FAVORITES_LIMIT}).\n_Избранное заполнено._"
        hist = conn.execute(
            "SELECT * FROM history WHERE id=? AND user_id=?", (hist_id, user_id)
        ).fetchone()
        if not hist:
            return False, "⚠️ Тарих табылмады."
        existing = conn.execute(
            "SELECT id FROM favorites WHERE user_id=? AND material_name=? AND topic=?",
            (user_id, hist["material_name"], hist["topic"]),
        ).fetchone()
        if existing:
            return False, "⭐ Бұрын сақталған!\n_Уже в избранном!_"
        conn.execute(
            "INSERT INTO favorites (user_id, section, material_name, material_type, "
            "topic, result, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, hist["section"], hist["material_name"], hist["material_type"],
             hist["topic"], hist["result"], _now()),
        )
        return True, "⭐ Таңдаулыларға сақталды!\n_Добавлено в избранное!_"


def remove_favorite(user_id: int, fav_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM favorites WHERE id=? AND user_id=?", (fav_id, user_id))


def get_favorites(user_id: int) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM favorites WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
        return [_row(r) for r in rows]


def get_favorite_item(fav_id: int, user_id: int) -> dict:
    with _conn() as conn:
        return _row(conn.execute(
            "SELECT * FROM favorites WHERE id=? AND user_id=?", (fav_id, user_id)
        ).fetchone())


def activate_plan(user_id: int, plan: str, days: int = 30) -> bool:
    if plan not in TARIFFS:
        return False
    now = datetime.utcnow()
    expires = (now + timedelta(days=days)).isoformat()
    mk = _month_key()
    with _conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO users (user_id, plan, activated_at, expires_at, reset_month, "
                "first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, plan, now.isoformat(), expires, mk, now.isoformat(), now.isoformat()),
            )
        else:
            conn.execute(
                "UPDATE users SET plan=?, activated_at=?, expires_at=?, "
                "text_used=0, poster_used=0, music_used=0, reset_month=? WHERE user_id=?",
                (plan, now.isoformat(), expires, mk, user_id),
            )
    return True


def get_expiring_users(days: int = 3) -> list:
    target = (datetime.utcnow() + timedelta(days=days)).date().isoformat()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE plan != 'free' AND expires_at IS NOT NULL "
            "AND substr(expires_at, 1, 10) = ?",
            (target,),
        ).fetchall()
        return [_row(r) for r in rows]


def downgrade_expired_users() -> list:
    """Downgrade expired paid plans to basic. Returns list of affected user_ids."""
    today = datetime.utcnow().date().isoformat()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT user_id, plan FROM users WHERE plan NOT IN ('free','basic') "
            "AND expires_at IS NOT NULL AND substr(expires_at, 1, 10) < ?",
            (today,),
        ).fetchall()
        ids = [r["user_id"] for r in rows]
        if ids:
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE users SET plan='basic', expires_at=NULL WHERE user_id IN ({placeholders})",
                ids,
            )
        return ids


def get_stats() -> dict:
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        plan_counts = {p: 0 for p in TARIFFS}
        for p in TARIFFS:
            plan_counts[p] = conn.execute(
                "SELECT COUNT(*) FROM users WHERE plan=?", (p,)
            ).fetchone()[0]
        text_total = conn.execute("SELECT COALESCE(SUM(text_total),0) FROM users").fetchone()[0]
        poster_total = conn.execute("SELECT COALESCE(SUM(poster_total),0) FROM users").fetchone()[0]
        music_total = conn.execute("SELECT COALESCE(SUM(music_total),0) FROM users").fetchone()[0]
        today_str = date.today().isoformat()
        today_gen = conn.execute(
            "SELECT COUNT(*) FROM history WHERE substr(created_at,1,10)=?", (today_str,)
        ).fetchone()[0]
        month_prefix = date.today().strftime("%Y-%m")
        revenue = 0
        for plan, data in TARIFFS.items():
            if plan == "free" or not data["price"]:
                continue
            c = conn.execute(
                "SELECT COUNT(*) FROM users WHERE plan=? AND activated_at IS NOT NULL "
                "AND substr(activated_at,1,7)=?",
                (plan, month_prefix),
            ).fetchone()[0]
            revenue += c * data["price"]
    return {
        "total_users": total,
        "plan_counts": plan_counts,
        "text_total": text_total,
        "poster_total": poster_total,
        "music_total": music_total,
        "today_gen": today_gen,
        "revenue": revenue,
    }


def get_all_users(limit: int = 20) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY last_seen DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row(r) for r in rows]


def get_users_for_broadcast(plan_filter: str = "all") -> list:
    with _conn() as conn:
        if plan_filter != "all":
            rows = conn.execute(
                "SELECT user_id FROM users WHERE plan=?", (plan_filter,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r["user_id"] for r in rows]
