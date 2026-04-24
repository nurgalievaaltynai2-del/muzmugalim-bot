import urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import SECTIONS, PAGE_SIZE, TARIFFS, PLAN_RANK, MType

_WHATSAPP_NUMBER = "77073078874"
_WHATSAPP_URL = f"https://wa.me/{_WHATSAPP_NUMBER}"

_PLAN_ICON = {"free": "🆓", "basic": "🥉", "standard": "🥈", "premium": "🥇", "full": "👑"}
_TYPE_ICON = {"text": "📝", "poster": "🖼️", "music": "🎵"}


# ─── Language selection ───────────────────────────────────────────────────────

def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang:kz"),
            InlineKeyboardButton("🇷🇺 Русский",  callback_data="lang:ru"),
        ]
    ])


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏫 Мектеп",    callback_data="section:mektep"),
            InlineKeyboardButton("🎪 Балабақша", callback_data="section:balabaqsha"),
        ],
        [InlineKeyboardButton("✨ Мүмкіндіктер мен тарифтер", callback_data="tarif")],
        [InlineKeyboardButton("👤 Профиль / Профиль",         callback_data="profile")],
        [InlineKeyboardButton("📞 Жазылу → @muzmugalim", url="https://t.me/muzmugalim")],
    ])


# ─── Tariff keyboards ─────────────────────────────────────────────────────────

def tarif_card_kb(plan: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Осыны таңдаймын / Выбрать",
            callback_data=f"tarif_select:{plan}",
        )],
    ])


def payment_kb(plan: str) -> InlineKeyboardMarkup:
    price = TARIFFS[plan]["price"]
    wa_text = f"Мен {TARIFFS[plan]['name']} тарифін таңдадым ({price} тг). Чек жіберемін."
    wa_url = f"{_WHATSAPP_URL}?text={urllib.parse.quote(wa_text)}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📲 WhatsApp-қа чек жіберу", url=wa_url)],
        [InlineKeyboardButton("‹ Тарифтерге оралу",        callback_data="tarif")],
        [InlineKeyboardButton("🏠 Басты мәзір",             callback_data="main_menu")],
    ])


# ─── Material list ────────────────────────────────────────────────────────────

def material_list_kb(section: str, page: int, user_plan: str = "free") -> InlineKeyboardMarkup:
    materials = SECTIONS[section]["materials"]
    total = len(materials)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    user_rank = PLAN_RANK.get(user_plan, 0)

    items = []
    for idx in range(start, end):
        mat = materials[idx]
        locked = PLAN_RANK[mat.min_plan] > user_rank
        icon = _TYPE_ICON.get(mat.mtype, "📄")
        lock = "🔒" if locked else "✅"
        display = f"{mat.name} / {mat.name_ru}" if mat.name_ru else mat.name
        items.append((f"{lock} {icon} {display}", f"mat:{section}:{idx}", mat.mtype))

    rows = []
    i = 0
    while i < len(items):
        label, cb, mtype = items[i]
        if mtype in (MType.POSTER, MType.MUSIC):
            rows.append([InlineKeyboardButton(label, callback_data=cb)])
            i += 1
        elif i + 1 < len(items) and items[i + 1][2] not in (MType.POSTER, MType.MUSIC):
            label2, cb2, _ = items[i + 1]
            rows.append([
                InlineKeyboardButton(label,  callback_data=cb),
                InlineKeyboardButton(label2, callback_data=cb2),
            ])
            i += 2
        else:
            rows.append([InlineKeyboardButton(label, callback_data=cb)])
            i += 1

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"page:{section}:{page - 1}"))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"page:{section}:{page + 1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🏠 Басты мәзір", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def back_to_list_kb(section: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹ Тізімге оралу", callback_data=f"page:{section}:{page}")],
        [InlineKeyboardButton("🏠 Басты мәзір",  callback_data="main_menu")],
    ])


def upgrade_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Тариф таңдау", callback_data="tarif")],
        [InlineKeyboardButton("🏠 Басты мәзір",  callback_data="main_menu")],
    ])


# ─── Result actions (shown after generation) ─────────────────────────────────

def result_kb(hist_id: int, section: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ Сақтау / Сохранить", callback_data=f"fav:add:{hist_id}"),
            InlineKeyboardButton("📄 PDF",                 callback_data=f"pdf:{hist_id}"),
        ],
        [InlineKeyboardButton("📤 Бөлісу / Поделиться",  callback_data=f"share:{hist_id}")],
        [InlineKeyboardButton("‹ Тізімге оралу",          callback_data=f"page:{section}:{page}")],
        [InlineKeyboardButton("🏠 Басты мәзір",           callback_data="main_menu")],
    ])


# ─── Profile ──────────────────────────────────────────────────────────────────

def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Тарих / История",      callback_data="history"),
            InlineKeyboardButton("⭐ Таңдаулылар / Избранное", callback_data="favorites"),
        ],
        [InlineKeyboardButton("💎 Тариф ауыстыру / Сменить", callback_data="tarif")],
        [InlineKeyboardButton("🏠 Басты мәзір",              callback_data="main_menu")],
    ])


# ─── History ──────────────────────────────────────────────────────────────────

def history_kb(items: list) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        icon = _TYPE_ICON.get(item["material_type"], "📄")
        date_str = item["created_at"][:10]
        topic_short = item["topic"][:18] + ("…" if len(item["topic"]) > 18 else "")
        label = f"{icon} {item['material_name']} — {topic_short} ({date_str})"
        rows.append([InlineKeyboardButton(label, callback_data=f"hist_item:{item['id']}")])
    rows.append([InlineKeyboardButton("🏠 Басты мәзір", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def hist_item_kb(hist_id: int, section: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ Сақтау",          callback_data=f"fav:add:{hist_id}"),
            InlineKeyboardButton("📄 PDF",             callback_data=f"pdf:{hist_id}"),
        ],
        [InlineKeyboardButton("🔄 Қайта жасау / Перегенерировать", callback_data=f"regen:{hist_id}")],
        [InlineKeyboardButton("‹ Тарихқа оралу",      callback_data="history")],
        [InlineKeyboardButton("🏠 Басты мәзір",        callback_data="main_menu")],
    ])


# ─── Favorites ────────────────────────────────────────────────────────────────

def favorites_kb(items: list) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        icon = _TYPE_ICON.get(item["material_type"], "📄")
        topic_short = item["topic"][:20] + ("…" if len(item["topic"]) > 20 else "")
        label = f"{icon} {item['material_name']} — {topic_short}"
        rows.append([InlineKeyboardButton(label, callback_data=f"fav_item:{item['id']}")])
    rows.append([InlineKeyboardButton("🏠 Басты мәзір", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def fav_item_kb(fav_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 PDF",              callback_data=f"pdf_fav:{fav_id}"),
            InlineKeyboardButton("🗑️ Өшіру / Удалить", callback_data=f"fav:remove:{fav_id}"),
        ],
        [InlineKeyboardButton("🔄 Қайта жасау",         callback_data=f"regen_fav:{fav_id}")],
        [InlineKeyboardButton("‹ Таңдаулыларға оралу",  callback_data="favorites")],
        [InlineKeyboardButton("🏠 Басты мәзір",          callback_data="main_menu")],
    ])


# ─── Admin panel ──────────────────────────────────────────────────────────────

def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Мұғалімдер",  callback_data="admin:users"),
            InlineKeyboardButton("📢 Хабарлама",   callback_data="admin:broadcast"),
        ],
        [
            InlineKeyboardButton("💰 Тариф беру",  callback_data="admin:giveplan"),
            InlineKeyboardButton("📊 Толық есеп",  callback_data="admin:fullstats"),
        ],
        [InlineKeyboardButton("🏠 Басты мәзір",    callback_data="main_menu")],
    ])


def broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Барлығына / Всем",       callback_data="broadcast:all")],
        [
            InlineKeyboardButton("🥉 Базалық",             callback_data="broadcast:basic"),
            InlineKeyboardButton("🥈 Стандарт",            callback_data="broadcast:standard"),
        ],
        [
            InlineKeyboardButton("🥇 Премиум",             callback_data="broadcast:premium"),
            InlineKeyboardButton("👑 Толық",               callback_data="broadcast:full"),
        ],
        [InlineKeyboardButton("‹ Артқа / Назад",           callback_data="admin_panel")],
    ])
