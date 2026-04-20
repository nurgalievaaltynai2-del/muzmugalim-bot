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


def ensure_user(tg_user) -> dict:
    data = _load()
    uid = str(tg_user.id)
    now = datetime.utcnow().isoformat()
    today_month_start = date.today().replace(day=1).isoformat()
    if uid not in data:
        data[uid] = {
            "user_id": tg_user.id,
            "username": tg_user.username,
            "first_name": tg_user.first_name,
            "plan": "free",
            "activated_at": None,
            "reset_date": today_month_start,
            "usage_total": 0,
            "usage_this_month": 0,
            "first_seen": now,
            "last_seen": now,
        }
    else:
        data[uid]["last_seen"] = now
        data[uid]["username"] = tg_user.username
    _save(data)
    return data[uid]


def _maybe_reset_monthly(record: dict) -> dict:
    today_month_start = date.today().replace(day=1).isoformat()
    if record.get("reset_date") != today_month_start:
        record["usage_this_month"] = 0
        record["reset_date"] = today_month_start
    return record


def check_quota(user_id: int) -> tuple:
    data = _load()
    uid = str(user_id)
    if uid not in data:
        return False, "Пайдаланушы табылмады"
    record = _maybe_reset_monthly(data[uid])
    plan = record["plan"]
    tariff = TARIFFS[plan]

    if plan == "free":
        if record["usage_total"] >= tariff["limit"]:
            return False, (
                f"⚠️ Тегін пайдалану лимиті аяқталды ({tariff['limit']} сұраныс).\n\n"
                "Жазылу үшін /tarif командасын немесе 💰 Тариф батырмасын басыңыз.\n"
                "Байланыс: @muzmugalim"
            )
    elif tariff["limit"] is not None:
        if record["usage_this_month"] >= tariff["limit"]:
            return False, (
                f"⚠️ Ай лимиті аяқталды ({tariff['limit']} сұраныс/ай).\n\n"
                "Жоғарырақ тарифке ауысу үшін @muzmugalim-ге хабарласыңыз."
            )

    _save(data)
    return True, ""


def record_usage(user_id: int):
    data = _load()
    uid = str(user_id)
    if uid not in data:
        return
    record = _maybe_reset_monthly(data[uid])
    record["usage_total"] += 1
    record["usage_this_month"] += 1
    data[uid] = record
    _save(data)


def activate_plan(user_id: int, plan: str) -> bool:
    if plan not in TARIFFS:
        return False
    data = _load()
    uid = str(user_id)
    today_month_start = date.today().replace(day=1).isoformat()
    now = datetime.utcnow().isoformat()
    if uid not in data:
        data[uid] = {
            "user_id": user_id,
            "username": None,
            "first_name": None,
            "plan": plan,
            "activated_at": now,
            "reset_date": today_month_start,
            "usage_total": 0,
            "usage_this_month": 0,
            "first_seen": now,
            "last_seen": now,
        }
    else:
        data[uid]["plan"] = plan
        data[uid]["activated_at"] = now
        data[uid]["usage_this_month"] = 0
        data[uid]["reset_date"] = today_month_start
    _save(data)
    return True


def get_user_info(user_id: int) -> dict | None:
    data = _load()
    return data.get(str(user_id))
