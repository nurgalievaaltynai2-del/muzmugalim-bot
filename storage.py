import json
import os
from datetime import datetime, date

from config import USERS_FILE, TARIFFS


def _load() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _month_start() -> str:
    return date.today().replace(day=1).isoformat()


def ensure_user(tg_user) -> dict:
    data = _load()
    uid = str(tg_user.id)
    now = datetime.utcnow().isoformat()
    if uid not in data:
        data[uid] = {
            "user_id": tg_user.id,
            "username": tg_user.username,
            "first_name": tg_user.first_name,
            "plan": "free",
            "activated_at": None,
            "reset_date": _month_start(),
            "text_used": 0,
            "poster_used": 0,
            "music_used": 0,
            "first_seen": now,
            "last_seen": now,
        }
    else:
        data[uid]["last_seen"] = now
        data[uid]["username"] = tg_user.username
    _save(data)
    return data[uid]


def _maybe_reset_monthly(record: dict) -> dict:
    if record.get("reset_date") != _month_start():
        record["poster_used"] = 0
        record["music_used"] = 0
        record["reset_date"] = _month_start()
        if record.get("plan") != "free":
            record["text_used"] = 0
    return record


def check_quota(user_id: int, mtype: str) -> tuple:
    """
    Check if user can use a feature.
    mtype: 'text', 'poster', 'music'
    Returns (allowed: bool, reason: str)
    """
    data = _load()
    uid = str(user_id)
    if uid not in data:
        return False, "Пайдаланушы табылмады"

    record = _maybe_reset_monthly(data[uid])
    plan = record["plan"]
    tariff = TARIFFS[plan]
    limit = tariff[mtype]

    if mtype == "text":
        if plan == "free" and record["text_used"] >= limit:
            return False, (
                f"⚠️ Тегін лимит аяқталды ({limit} сұраныс).\n\n"
                "Жалғастыру үшін тариф таңдаңыз 👇"
            )
        # paid plans: text is unlimited (limit=None)

    elif mtype == "poster":
        if limit == 0:
            return False, "no_poster_access"
        if limit is not None and record["poster_used"] >= limit:
            return False, (
                f"⚠️ Постер лимиті аяқталды ({limit}/ай).\n\n"
                "Жоғарырақ тарифке ауысу үшін @muzmugalim-ге хабарласыңыз."
            )

    elif mtype == "music":
        if limit == 0:
            return False, "no_music_access"
        if limit is not None and record["music_used"] >= limit:
            return False, (
                f"⚠️ Музыка лимиті аяқталды ({limit}/ай).\n\n"
                "Жоғарырақ тарифке ауысу үшін @muzmugalim-ге хабарласыңыз."
            )

    data[uid] = record
    _save(data)
    return True, ""


def record_usage(user_id: int, mtype: str):
    data = _load()
    uid = str(user_id)
    if uid not in data:
        return
    record = _maybe_reset_monthly(data[uid])
    field = f"{mtype}_used"
    record[field] = record.get(field, 0) + 1
    data[uid] = record
    _save(data)


def activate_plan(user_id: int, plan: str) -> bool:
    if plan not in TARIFFS:
        return False
    data = _load()
    uid = str(user_id)
    now = datetime.utcnow().isoformat()
    if uid not in data:
        data[uid] = {
            "user_id": user_id,
            "username": None,
            "first_name": None,
            "plan": plan,
            "activated_at": now,
            "reset_date": _month_start(),
            "text_used": 0,
            "poster_used": 0,
            "music_used": 0,
            "first_seen": now,
            "last_seen": now,
        }
    else:
        data[uid]["plan"] = plan
        data[uid]["activated_at"] = now
        data[uid]["poster_used"] = 0
        data[uid]["music_used"] = 0
        data[uid]["text_used"] = 0
        data[uid]["reset_date"] = _month_start()
    _save(data)
    return True


def get_stats() -> dict:
    data = _load()
    plan_counts = {p: 0 for p in TARIFFS}
    text_total = poster_total = music_total = 0
    for rec in data.values():
        plan_counts[rec.get("plan", "free")] = plan_counts.get(rec.get("plan", "free"), 0) + 1
        text_total += rec.get("text_used", 0)
        poster_total += rec.get("poster_used", 0)
        music_total += rec.get("music_used", 0)
    return {
        "total_users": len(data),
        "plan_counts": plan_counts,
        "text_total": text_total,
        "poster_total": poster_total,
        "music_total": music_total,
    }


def get_all_users(limit: int = 20) -> list:
    data = _load()
    users = list(data.values())
    users.sort(key=lambda u: u.get("last_seen", ""), reverse=True)
    return users[:limit]
