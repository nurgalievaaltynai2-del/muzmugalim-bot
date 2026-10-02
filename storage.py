import os
import psycopg2
import psycopg2.extras
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from config import TARIFFS

_DATABASE_URL = os.getenv("DATABASE_URL", "")
_HISTORY_LIMIT = 10
_FAVORITES_LIMIT = 20


@contextmanager
def _conn():
    conn = psycopg2.connect(_DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _row(r) -> dict:
    return dict(r) if r else {}


def init_db():
    with _conn() as conn:
        c = _cur(conn)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      BIGINT PRIMARY KEY,
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id            SERIAL PRIMARY KEY,
                user_id       BIGINT NOT NULL REFERENCES users(user_id),
                section       TEXT NOT NULL,
                material_name TEXT NOT NULL,
                material_type TEXT NOT NULL,
                topic         TEXT NOT NULL,
                result        TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id            SERIAL PRIMARY KEY,
                user_id       BIGINT NOT NULL REFERENCES users(user_id),
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
    c = _cur(conn)
    c.execute("SELECT reset_month FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone()
    if row and row["reset_month"] != mk:
        c.execute(
            "UPDATE users SET text_used=0, poster_used=0, music_used=0, reset_month=%s "
            "WHERE user_id=%s",
            (mk, user_id),
        )


def ensure_user(tg_user) -> dict:
    now = _now()
    mk = _month_key()
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT * FROM users WHERE user_id=%s", (tg_user.id,))
        row = c.fetchone()
        if row is None:
            c.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, "
                "plan, reset_month, first_seen, last_seen) VALUES (%s, %s, %s, %s, 'free', %s, %s, %s)",
                (tg_user.id, tg_user.username, tg_user.first_name,
                 getattr(tg_user, "last_name", None), mk, now, now),
            )
        else:
            c.execute(
                "UPDATE users SET username=%s, first_name=%s, last_name=%s, last_seen=%s "
                "WHERE user_id=%s",
                (tg_user.username, tg_user.first_name,
                 getattr(tg_user, "last_name", None), now, tg_user.id),
            )
            _reset_if_new_month(conn, tg_user.id)
        c.execute("SELECT * FROM users WHERE user_id=%s", (tg_user.id,))
        return _row(c.fetchone())


def check_quota(user_id: int, mtype: str) -> tuple:
    with _conn() as conn:
        _reset_if_new_month(conn, user_id)
        c = _cur(conn)
        c.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
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
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
        if not row:
            return 0, 0
        plan = row["plan"]
        lim = TARIFFS[plan][mtype]
        used = row[f"{mtype}_used"]
        return used, lim


def record_usage(user_id: int, mtype: str):
    with _conn() as conn:
        c = _cur(conn)
        c.execute(
            f"UPDATE users SET {mtype}_used={mtype}_used+1, {mtype}_total={mtype}_total+1 "
            "WHERE user_id=%s",
            (user_id,),
        )


def save_history(user_id: int, section: str, material_name: str,
                 material_type: str, topic: str, result: str) -> int:
    with _conn() as conn:
        c = _cur(conn)
        c.execute(
            "INSERT INTO history (user_id, section, material_name, material_type, "
            "topic, result, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (user_id, section, material_name, material_type, topic, result[:4000], _now()),
        )
        hist_id = c.fetchone()["id"]
        c.execute(
            "DELETE FROM history WHERE user_id=%s AND id NOT IN "
            "(SELECT id FROM history WHERE user_id=%s ORDER BY id DESC LIMIT %s)",
            (user_id, user_id, _HISTORY_LIMIT),
        )
        return hist_id


def get_history(user_id: int) -> list:
    with _conn() as conn:
        c = _cur(conn)
        c.execute(
            "SELECT * FROM history WHERE user_id=%s ORDER BY id DESC LIMIT %s",
            (user_id, _HISTORY_LIMIT),
        )
        return [_row(r) for r in c.fetchall()]


def get_history_item(hist_id: int, user_id: int) -> dict:
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT * FROM history WHERE id=%s AND user_id=%s", (hist_id, user_id))
        return _row(c.fetchone())


def add_favorite(user_id: int, hist_id: int) -> tuple:
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT COUNT(*) as cnt FROM favorites WHERE user_id=%s", (user_id,))
        count = c.fetchone()["cnt"]
        if count >= _FAVORITES_LIMIT:
            return False, f"⚠️ Таңдаулылар толы (макс {_FAVORITES_LIMIT}).\n_Избранное заполнено._"
        c.execute("SELECT * FROM history WHERE id=%s AND user_id=%s", (hist_id, user_id))
        hist = c.fetchone()
        if not hist:
            return False, "⚠️ Тарих табылмады."
        c.execute(
            "SELECT id FROM favorites WHERE user_id=%s AND material_name=%s AND topic=%s",
            (user_id, hist["material_name"], hist["topic"]),
        )
        if c.fetchone():
            return False, "⭐ Бұрын сақталған!\n_Уже в избранном!_"
        c.execute(
            "INSERT INTO favorites (user_id, section, material_name, material_type, "
            "topic, result, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user_id, hist["section"], hist["material_name"], hist["material_type"],
             hist["topic"], hist["result"], _now()),
        )
        return True, "⭐ Таңдаулыларға сақталды!\n_Добавлено в избранное!_"


def remove_favorite(user_id: int, fav_id: int):
    with _conn() as conn:
        c = _cur(conn)
        c.execute("DELETE FROM favorites WHERE id=%s AND user_id=%s", (fav_id, user_id))


def get_favorites(user_id: int) -> list:
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT * FROM favorites WHERE user_id=%s ORDER BY id DESC", (user_id,))
        return [_row(r) for r in c.fetchall()]


def get_favorite_item(fav_id: int, user_id: int) -> dict:
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT * FROM favorites WHERE id=%s AND user_id=%s", (fav_id, user_id))
        return _row(c.fetchone())


def activate_plan(user_id: int, plan: str, days: int = 30) -> bool:
    if plan not in TARIFFS:
        return False
    now = datetime.utcnow()
    expires = (now + timedelta(days=days)).isoformat()
    mk = _month_key()
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
        if not row:
            c.execute(
                "INSERT INTO users (user_id, plan, activated_at, expires_at, reset_month, "
                "first_seen, last_seen) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (user_id, plan, now.isoformat(), expires, mk, now.isoformat(), now.isoformat()),
            )
        else:
            c.execute(
                "UPDATE users SET plan=%s, activated_at=%s, expires_at=%s, "
                "text_used=0, poster_used=0, music_used=0, reset_month=%s WHERE user_id=%s",
                (plan, now.isoformat(), expires, mk, user_id),
            )
    return True


def get_expiring_users(days: int = 3) -> list:
    target = (datetime.utcnow() + timedelta(days=days)).date().isoformat()
    with _conn() as conn:
        c = _cur(conn)
        c.execute(
            "SELECT * FROM users WHERE plan != 'free' AND expires_at IS NOT NULL "
            "AND LEFT(expires_at, 10) = %s",
            (target,),
        )
        return [_row(r) for r in c.fetchall()]


def downgrade_expired_users() -> list:
    today = datetime.utcnow().date().isoformat()
    with _conn() as conn:
        c = _cur(conn)
        c.execute(
            "SELECT user_id FROM users WHERE plan NOT IN ('free','basic') "
            "AND expires_at IS NOT NULL AND LEFT(expires_at, 10) < %s",
            (today,),
        )
        ids = [r["user_id"] for r in c.fetchall()]
        if ids:
            c.execute(
                "UPDATE users SET plan='basic', expires_at=NULL WHERE user_id = ANY(%s)",
                (ids,),
            )
        return ids


def get_stats() -> dict:
    with _conn() as conn:
        c = _cur(conn)
        c.execute("SELECT COUNT(*) as cnt FROM users")
        total = c.fetchone()["cnt"]
        plan_counts = {p: 0 for p in TARIFFS}
        for p in TARIFFS:
            c.execute("SELECT COUNT(*) as cnt FROM users WHERE plan=%s", (p,))
            plan_counts[p] = c.fetchone()["cnt"]
        c.execute("SELECT COALESCE(SUM(text_total),0) as cnt FROM users")
        text_total = c.fetchone()["cnt"]
        c.execute("SELECT COALESCE(SUM(poster_total),0) as cnt FROM users")
        poster_total = c.fetchone()["cnt"]
        c.execute("SELECT COALESCE(SUM(music_total),0) as cnt FROM users")
        music_total = c.fetchone()["cnt"]
        today_str = date.today().isoformat()
        c.execute(
            "SELECT COUNT(*) as cnt FROM history WHERE LEFT(created_at,10)=%s", (today_str,)
        )
        today_gen = c.fetchone()["cnt"]
        month_prefix = date.today().strftime("%Y-%m")
        revenue = 0
        for plan, data in TARIFFS.items():
            if plan == "free" or not data["price"]:
                continue
            c.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE plan=%s AND activated_at IS NOT NULL "
                "AND LEFT(activated_at,7)=%s",
                (plan, month_prefix),
            )
            revenue += c.fetchone()["cnt"] * data["price"]
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
        c = _cur(conn)
        c.execute("SELECT * FROM users ORDER BY last_seen DESC LIMIT %s", (limit,))
        return [_row(r) for r in c.fetchall()]


def get_users_for_broadcast(plan_filter: str = "all") -> list:
    with _conn() as conn:
        c = _cur(conn)
        if plan_filter != "all":
            c.execute("SELECT user_id FROM users WHERE plan=%s", (plan_filter,))
        else:
            c.execute("SELECT user_id FROM users")
        return [r["user_id"] for r in c.fetchall()]
