import io
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

import generators
import pdf_gen
from config import SECTIONS, TARIFFS, PLAN_RANK, ADMIN_ID, MType
from keyboards import (
    main_menu_kb, material_list_kb, back_to_list_kb,
    tarif_card_kb, upgrade_kb, payment_kb, result_kb,
    profile_kb, history_kb, hist_item_kb,
    favorites_kb, fav_item_kb,
    admin_kb, broadcast_kb, lang_kb,
)
from storage import (
    init_db,
    ensure_user, check_quota, record_usage, get_remaining,
    save_history, get_history, get_history_item,
    add_favorite, remove_favorite, get_favorites, get_favorite_item,
    activate_plan, get_stats, get_all_users, get_users_for_broadcast,
)

logger = logging.getLogger(__name__)

init_db()

# ─── Static texts ─────────────────────────────────────────────────────────────

MAIN_MENU_TEXT = (
    "🎼 *MuzMugalim* — музыка мұғалімінің AI көмекшісі\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Сабаққа дайындалу енді *секундтарда:*\n\n"
    "📝 Сабақ жоспары, тест, ноталар\n"
    "🎨 Сурет — DALL-E 3 AI суреттер\n"
    "🎵 Музыка MP3 — Suno AI\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "👇 *Бөлімді таңдаңыз:*"
)

MAIN_MENU_TEXT_RU = (
    "🎼 *MuzMugalim* — AI-помощник учителя музыки\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Подготовка к уроку теперь *за секунды:*\n\n"
    "📝 План урока, тесты, ноты\n"
    "🎨 Картинки — DALL-E 3 AI\n"
    "🎵 Музыка MP3 — Suno AI\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "👇 *Выберите раздел:*"
)

HELP_TEXT = (
    "📖 *MuzMugalim — Нұсқаулық*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "1️⃣ Бөлім таңдаңыз: Мектеп немесе Балабақша\n"
    "2️⃣ Материал түрін таңдаңыз\n"
    "3️⃣ Тақырып жазыңыз — AI дайындайды!\n\n"
    "🏫 *Мектеп* — 31 мүмкіндік (29 материал)\n"
    "🎪 *Балабақша* — 47 мүмкіндік (46 материал)\n\n"
    "🤖 *AI қозғалтқыштары:*\n"
    "  📝 Gemini 2.5 Flash — мәтін\n"
    "  🎨 DALL-E 3 — сурет\n"
    "  🎵 Suno AI — музыка MP3\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "💳 Kaspi: *8 707 307 88 74*  |  WA: @muzmugalim"
)

TARIF_INTRO = (
    "💎 *Тариф жоспарлары / Тарифные планы*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "_Тариф таңдап, кнопканы басыңыз 👇_\n"
    "_Выберите тариф и нажмите кнопку 👇_"
)

TARIF_CARDS = {
    "basic": (
        "🥉 ══════════════════ 🥉\n"
        "         *БАЗАЛЫҚ*\n"
        "   ━━━━━━━━━━━━━━━━\n"
        "        *4 490 ₸/ай*\n"
        "🥉 ══════════════════ 🥉\n\n"
        "📝 *Барлық мәтін ШЕКСІЗ:*\n\n"
        "🏫 *Мектеп (21 материал):*\n"
        "▸ Көрнекілік · Презентация · Тест\n"
        "▸ ҚМЖ/КТЖ · Сабақ жоспары · Рубрика\n"
        "▸ Ноталар · Музыкалық диктант\n"
        "▸ Дауыс жаттығулары · Сергіту сәті\n"
        "▸ Ән сөздері · Балалар әндері\n"
        "▸ Репертуар тізімі · Хор жоспары\n"
        "▸ Ата-анаға хат · Викторина · Кросворд\n"
        "▸ Музыкалық ойын · Саусақ ойыны\n\n"
        "🎪 *Балабақша (27 материал):*\n"
        "▸ Жылдық жоспар · Айлық жоспар\n"
        "▸ Аптасабақ · Логоритмика · Би жоспары\n"
        "▸ Таңғы гимнастика · Сергіту · + тағы басқа"
    ),
    "standard": (
        "🥈 ══════════════════ 🥈\n"
        "        *СТАНДАРТ*\n"
        "   ━━━━━━━━━━━━━━━━\n"
        "        *6 990 ₸/ай*\n"
        "🥈 ══════════════════ 🥈\n\n"
        "✅ Базалықтың *БАРЛЫҒЫ* +\n\n"
        "🎨 *DALL-E 3 Сурет — 30/ай*\n"
        "📁 *Портфолио*\n"
        "▸ Мектеп + Балабақша бөлімдері"
    ),
    "premium": (
        "🥇 ══════════════════ 🥇\n"
        "        *ПРЕМИУМ*\n"
        "   ━━━━━━━━━━━━━━━━\n"
        "       *10 990 ₸/ай*\n"
        "🥇 ══════════════════ 🥇\n\n"
        "✅ Стандарттың *БАРЛЫҒЫ* +\n\n"
        "🎵 *Suno AI Музыка — 10/ай*\n"
        "🎨 *Сурет — 50/ай*\n"
        "▸ Рефлексия · Дифф. тапсырма\n"
        "▸ Балабақша: Музыка терапия\n"
        "▸ Бейімдеу · Даму картасы"
    ),
    "full": (
        "👑 ══════════════════ 👑\n"
        "         *ТОЛЫҚ*\n"
        "   ━━━━━━━━━━━━━━━━\n"
        "       *14 990 ₸/ай*\n"
        "👑 ══════════════════ 👑\n\n"
        "✅ Премиумның *БАРЛЫҒЫ* +\n\n"
        "🎵 *Музыка — 20/ай*\n"
        "🎨 *Сурет — 100/ай*\n"
        "🎭 *Барлық сценарийлер:*\n"
        "▸ Наурыз · Жаңа жыл · 8 Наурыз\n"
        "▸ 1 Маусым · Туған күн · Бітіру\n"
        "▸ Ертегі · Музыкалық ертегі\n"
        "▸ Қуыршақ театры · Утренник\n"
        "▸ Ашық есік · Ата-ана жиналысы\n"
        "▸ Мектеп + Балабақша ТОЛЫҚ"
    ),
}

_PLAN_ICON = {"free": "🆓", "basic": "🥉", "standard": "🥈", "premium": "🥇", "full": "👑"}
_TYPE_ICONS = {MType.TEXT: "📝", MType.POSTER: "🖼️", MType.MUSIC: "🎵"}
_TYPE_PROMPTS = {
    MType.TEXT:   "✏️ *Тақырыпты жазыңыз / Введите тему*\n\n_Мысалы: «Домбыра», «Моцарт», «Ән жанрлары»_",
    MType.POSTER: "🖼️ *Постер тақырыбы / Тема постера*\n\n_Мысалы: «Наурыз мерекесі», «Домбыра»_",
    MType.MUSIC:  "🎵 *Музыка тақырыбы / Тема музыки*\n\n_Мысалы: «Көктем», «Балалар биі»_",
}


async def _send_tarif_cards(chat_id: int, bot):
    for plan, text in TARIF_CARDS.items():
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=tarif_card_kb(plan),
            parse_mode="Markdown",
        )


# ─── Command handlers ─────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    name = update.effective_user.first_name or "Мұғалім"
    await update.message.reply_text(
        f"Сәлем, *{name}!* 👋\n\n"
        "🎼 *MuzMugalim* — музыка мұғалімінің AI көмекшісі\n\n"
        "Тілді таңдаңыз / Выберите язык:",
        reply_markup=lang_kb(),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def tariff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TARIF_INTRO, parse_mode="Markdown")
    await _send_tarif_cards(update.effective_chat.id, context.bot)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _show_profile(update.message, update.effective_user)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    items = get_history(update.effective_user.id)
    if not items:
        await update.message.reply_text(
            "📋 *Тарих бос / История пуста*\n\n"
            "_Материал жасаған соң осында көрінеді._",
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return
    await update.message.reply_text(
        f"📋 *Соңғы {len(items)} материал / Последние {len(items)} материалов:*",
        reply_markup=history_kb(items),
        parse_mode="Markdown",
    )


async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    items = get_favorites(update.effective_user.id)
    if not items:
        await update.message.reply_text(
            "⭐ *Таңдаулылар бос / Избранное пусто*\n\n"
            "_Материал жасаған соң ⭐ кнопкасын басыңыз._",
            parse_mode="Markdown",
            reply_markup=main_menu_kb(),
        )
        return
    await update.message.reply_text(
        f"⭐ *Таңдаулылар — {len(items)} материал / Избранное:*",
        reply_markup=favorites_kb(items),
        parse_mode="Markdown",
    )


async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Формат: /activate <user_id> <plan> [days]")
        return
    try:
        uid = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id сан болуы керек.")
        return
    plan = args[1].lower()
    days = int(args[2]) if len(args) >= 3 else 30
    if activate_plan(uid, plan, days):
        await update.message.reply_text(
            f"✅ `{uid}` пайдаланушысына *{plan}* тарифі {days} күнге белсендірілді.",
            parse_mode="Markdown",
        )
        try:
            plan_name = TARIFFS[plan]["name"]
            await context.bot.send_message(
                uid,
                f"🎉 *Тарифіңіз белсендірілді!*\n\n"
                f"📦 {plan_name} тарифі {days} күнге қосылды.\n"
                f"Пайдалануды бастаңыз 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_kb(),
            )
        except Exception:
            pass
    else:
        valid = ", ".join(TARIFFS.keys())
        await update.message.reply_text(f"❌ Белгісіз тариф. Қолжетімдісі: {valid}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    await _send_admin_panel(update.message)


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    await _send_users_list(update.message)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    await _send_admin_panel(update.message)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    await update.message.reply_text(
        "📢 *Хабарлама жіберу / Рассылка*\n\n"
        "_Кімге жіберу керек?_\n_Кому отправить?_",
        reply_markup=broadcast_kb(),
        parse_mode="Markdown",
    )


# ─── Helper: profile display ──────────────────────────────────────────────────

async def _show_profile(message, tg_user):
    user = ensure_user(tg_user)
    plan = user.get("plan", "free")
    plan_icon = _PLAN_ICON.get(plan, "🆓")
    plan_name = TARIFFS.get(plan, {}).get("name", "Тегін")

    name_parts = [tg_user.first_name or ""]
    if getattr(tg_user, "last_name", None):
        name_parts.append(tg_user.last_name)
    full_name = " ".join(p for p in name_parts if p) or "Мұғалім"

    expires_at = user.get("expires_at")
    if expires_at:
        try:
            exp = datetime.strptime(expires_at[:10], "%Y-%m-%d")
            expiry_line = f"📅 Мерзімі: *{exp.strftime('%d.%m.%Y')}* дейін / до\n"
        except ValueError:
            expiry_line = ""
    else:
        expiry_line = ""

    poster_used, poster_lim = get_remaining(tg_user.id, "poster")
    music_used, music_lim = get_remaining(tg_user.id, "music")
    total_gen = (user.get("text_total", 0) + user.get("poster_total", 0)
                 + user.get("music_total", 0))

    def fmt(used, lim):
        if lim is None:
            return "∞ шексіз"
        if lim == 0:
            return "—"
        return f"{lim - used}/{lim}"

    await message.reply_text(
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👩‍🏫 *{full_name}*\n"
        f"{plan_icon} *{plan_name}* тариф\n"
        f"{expiry_line}"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📊 *Статистика / Статистика:*\n"
        f"📝 Жасаған материал: *{total_gen}*\n"
        f"🖼️ Постер қалды: *{fmt(poster_used, poster_lim)}*\n"
        f"🎵 Музыка қалды: *{fmt(music_used, music_lim)}*\n"
        "━━━━━━━━━━━━━━━━━━━",
        reply_markup=profile_kb(),
        parse_mode="Markdown",
    )


# ─── Helper: admin panel ──────────────────────────────────────────────────────

async def _send_admin_panel(message):
    s = get_stats()
    plan_lines = "\n".join(
        f"  {_PLAN_ICON.get(p,'?')} {TARIFFS[p]['name']}: {c}"
        for p, c in s["plan_counts"].items() if c > 0
    )
    await message.reply_text(
        "━━━━━━━━━━━━━━━━━━━\n"
        "🛠️ *ADMIN PANEL*\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 *Статистика:*\n"
        f"👥 Барлық мұғалім: *{s['total_users']}*\n"
        f"💰 Ай табысы: *{s['revenue']:,} ₸*\n"
        f"📝 Бүгін жасалған: *{s['today_gen']}*\n\n"
        "📋 *Тарифтер:*\n"
        f"{plan_lines}\n\n"
        "━━━━━━━━━━━━━━━━━━━",
        reply_markup=admin_kb(),
        parse_mode="Markdown",
    )


async def _send_users_list(message):
    users = get_all_users(20)
    if not users:
        await message.reply_text("Қолданушылар жоқ.")
        return
    lines = []
    for u in users:
        name = f"@{u['username']}" if u.get("username") else u.get("first_name", str(u["user_id"]))
        plan = TARIFFS.get(u.get("plan", "free"), {}).get("name", "?")
        lines.append(
            f"{name} | {plan} | "
            f"📝{u.get('text_total', 0)} "
            f"🖼️{u.get('poster_total', 0)} "
            f"🎵{u.get('music_total', 0)}"
        )
    await message.reply_text(
        f"👥 *Соңғы {len(users)} қолданушы:*\n\n" + "\n".join(lines),
        parse_mode="Markdown",
    )


# ─── Helper: usage counter ────────────────────────────────────────────────────

def _usage_line(user_id: int, mtype: str) -> str:
    used, lim = get_remaining(user_id, mtype)
    if lim is None or lim == 0:
        return ""
    remaining = lim - used
    if remaining <= 5:
        return f"⚠️ *{remaining}/{lim}* қалды / осталось"
    return f"📊 *{remaining}/{lim}* қалды / осталось"


# ─── Helper: look up Russian material name ────────────────────────────────────

def _lookup_name_ru(section: str, material_name: str) -> str:
    for mat in SECTIONS.get(section, {}).get("materials", []):
        if mat.name == material_name:
            return mat.name_ru
    return ""


# ─── Callback handler ─────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = update.effective_user.id
    chat_id = query.message.chat_id

    if data == "noop":
        return

    # ── Language selection ──
    if data.startswith("lang:"):
        lang = data.split(":")[1]
        context.user_data["lang"] = lang
        user = ensure_user(update.effective_user)
        plan = user.get("plan", "free")
        plan_icon = _PLAN_ICON.get(plan, "💎")
        plan_name = TARIFFS.get(plan, {}).get("name", "")
        if lang == "ru":
            text = (
                MAIN_MENU_TEXT_RU
                + (f"\n\n{plan_icon} Тариф: *{plan_name}*" if plan != "free" else "")
            )
        else:
            text = (
                MAIN_MENU_TEXT
                + (f"\n\n{plan_icon} Тарифіңіз: *{plan_name}*" if plan != "free" else "")
            )
        await query.edit_message_text(text, reply_markup=main_menu_kb(), parse_mode="Markdown")
        return

    # ── Navigation ──
    if data == "main_menu":
        await query.edit_message_text(
            MAIN_MENU_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown"
        )

    elif data == "tarif":
        await query.edit_message_text(TARIF_INTRO, parse_mode="Markdown")
        await _send_tarif_cards(chat_id, context.bot)

    elif data == "profile":
        user = ensure_user(update.effective_user)
        plan = user.get("plan", "free")
        plan_icon = _PLAN_ICON.get(plan, "🆓")
        plan_name = TARIFFS.get(plan, {}).get("name", "Тегін")
        poster_used, poster_lim = get_remaining(uid, "poster")
        music_used, music_lim = get_remaining(uid, "music")
        total_gen = (user.get("text_total", 0) + user.get("poster_total", 0)
                     + user.get("music_total", 0))

        def fmt(used, lim):
            if lim is None:
                return "∞"
            if lim == 0:
                return "—"
            return f"{lim - used}/{lim}"

        expires_at = user.get("expires_at")
        expiry_line = ""
        if expires_at:
            try:
                exp = datetime.strptime(expires_at[:10], "%Y-%m-%d")
                expiry_line = f"📅 Мерзімі: *{exp.strftime('%d.%m.%Y')}* дейін\n"
            except ValueError:
                pass

        name = update.effective_user.first_name or "Мұғалім"
        await query.edit_message_text(
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👩‍🏫 *{name}*\n"
            f"{plan_icon} *{plan_name}* тариф\n"
            f"{expiry_line}"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📊 *Статистика:*\n"
            f"📝 Жасаған материал: *{total_gen}*\n"
            f"🖼️ Постер қалды: *{fmt(poster_used, poster_lim)}*\n"
            f"🎵 Музыка қалды: *{fmt(music_used, music_lim)}*\n"
            "━━━━━━━━━━━━━━━━━━━",
            reply_markup=profile_kb(),
            parse_mode="Markdown",
        )

    # ── Tariff selection ──
    elif data.startswith("tarif_select:"):
        plan = data.split(":")[1]
        await _show_payment(query, update, context, plan)

    # ── Section / page ──
    elif data.startswith("section:"):
        section = data.split(":")[1]
        context.user_data.update({"section": section, "page": 0, "waiting_topic": False})
        user = ensure_user(update.effective_user)
        await _show_list(query, section, 0, user["plan"])

    elif data.startswith("page:"):
        _, section, page_str = data.split(":")
        page = int(page_str)
        context.user_data.update({"section": section, "page": page, "waiting_topic": False})
        user = ensure_user(update.effective_user)
        await _show_list(query, section, page, user["plan"])

    # ── Material selection ──
    elif data.startswith("mat:"):
        _, section, idx_str = data.split(":")
        idx = int(idx_str)
        mat = SECTIONS[section]["materials"][idx]
        page = context.user_data.get("page", 0)
        user = ensure_user(update.effective_user)
        user_rank = PLAN_RANK.get(user["plan"], 0)

        if PLAN_RANK[mat.min_plan] > user_rank:
            needed = TARIFFS[mat.min_plan]["name"]
            await query.edit_message_text(
                f"🔒 *{mat.name}* — *{needed}* тарифінен қолжетімді.\n\n"
                "Жазылу үшін @muzmugalim-ге хабарласыңыз.",
                reply_markup=upgrade_kb(), parse_mode="Markdown",
            )
            return

        allowed, reason = check_quota(uid, mat.mtype)
        if not allowed:
            if reason == "no_poster_access":
                await query.edit_message_text(
                    f"🔒 Постер генерациясы *{TARIFFS['standard']['name']}* тарифінен.\n\n"
                    "Жазылу үшін @muzmugalim-ге хабарласыңыз.",
                    reply_markup=upgrade_kb(), parse_mode="Markdown",
                )
            elif reason == "no_music_access":
                await query.edit_message_text(
                    f"🔒 Музыка MP3 *{TARIFFS['premium']['name']}* тарифінен.\n\n"
                    "Жазылу үшін @muzmugalim-ге хабарласыңыз.",
                    reply_markup=upgrade_kb(), parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    reason, reply_markup=upgrade_kb(), parse_mode="Markdown"
                )
            return

        context.user_data.update({
            "section": section,
            "material_idx": idx,
            "material_name": mat.name,
            "material_name_ru": mat.name_ru,
            "material_type": mat.mtype,
            "page": page,
            "waiting_topic": True,
        })
        section_label = SECTIONS[section]["label"]
        await query.edit_message_text(
            f"{_TYPE_ICONS[mat.mtype]} *{mat.name}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 {section_label}\n\n"
            f"{_TYPE_PROMPTS[mat.mtype]}",
            reply_markup=back_to_list_kb(section, page),
            parse_mode="Markdown",
        )

    # ── History ──
    elif data == "history":
        items = get_history(uid)
        if not items:
            await query.edit_message_text(
                "📋 *Тарих бос*\n_История пуста_",
                reply_markup=main_menu_kb(), parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                f"📋 *Соңғы {len(items)} материал:*",
                reply_markup=history_kb(items), parse_mode="Markdown",
            )

    elif data.startswith("hist_item:"):
        hist_id = int(data.split(":")[1])
        item = get_history_item(hist_id, uid)
        if not item:
            await query.answer("⚠️ Табылмады", show_alert=True)
            return
        section = item.get("section", "mektep")
        icon = {"text": "📝", "poster": "🖼️", "music": "🎵"}.get(item["material_type"], "📄")
        date_str = item["created_at"][:10]
        preview = (item.get("result") or "")[:300]
        if len(item.get("result") or "") > 300:
            preview += "…"
        await query.edit_message_text(
            f"{icon} *{item['material_name']}* — {item['topic']}\n"
            f"📅 {date_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{preview}",
            reply_markup=hist_item_kb(hist_id, section),
            parse_mode="Markdown",
        )

    elif data.startswith("regen:"):
        hist_id = int(data.split(":")[1])
        item = get_history_item(hist_id, uid)
        if not item:
            await query.answer("⚠️ Табылмады", show_alert=True)
            return
        mtype_str = item["material_type"]
        mtype = MType(mtype_str)
        name_ru = _lookup_name_ru(item["section"], item["material_name"])
        context.user_data.update({
            "section": item["section"],
            "material_name": item["material_name"],
            "material_name_ru": name_ru,
            "material_type": mtype,
            "page": 0,
            "waiting_topic": True,
            "regen_topic": item["topic"],
        })
        await query.edit_message_text(
            f"🔄 *{item['material_name']}* қайта жасалуда…\n"
            f"_Тақырып: {item['topic']}_\n\n"
            f"Сол тақырыпты пайдалану үшін *{item['topic']}* жіберіңіз,\n"
            "немесе жаңа тақырып жазыңыз:",
            parse_mode="Markdown",
        )

    # ── Favorites ──
    elif data == "favorites":
        items = get_favorites(uid)
        if not items:
            await query.edit_message_text(
                "⭐ *Таңдаулылар бос*\n_Избранное пусто_",
                reply_markup=main_menu_kb(), parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                f"⭐ *Таңдаулылар — {len(items)}:*",
                reply_markup=favorites_kb(items), parse_mode="Markdown",
            )

    elif data.startswith("fav:add:"):
        hist_id = int(data.split(":")[2])
        ok, msg = add_favorite(uid, hist_id)
        await query.answer(msg, show_alert=not ok)

    elif data.startswith("fav:remove:"):
        fav_id = int(data.split(":")[2])
        remove_favorite(uid, fav_id)
        await query.answer("🗑️ Өшірілді / Удалено", show_alert=False)
        items = get_favorites(uid)
        if not items:
            await query.edit_message_text(
                "⭐ *Таңдаулылар бос*\n_Избранное пусто_",
                reply_markup=main_menu_kb(), parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                f"⭐ *Таңдаулылар — {len(items)}:*",
                reply_markup=favorites_kb(items), parse_mode="Markdown",
            )

    elif data.startswith("fav_item:"):
        fav_id = int(data.split(":")[1])
        item = get_favorite_item(fav_id, uid)
        if not item:
            await query.answer("⚠️ Табылмады", show_alert=True)
            return
        icon = {"text": "📝", "poster": "🖼️", "music": "🎵"}.get(item["material_type"], "📄")
        preview = (item.get("result") or "")[:300]
        if len(item.get("result") or "") > 300:
            preview += "…"
        await query.edit_message_text(
            f"⭐ {icon} *{item['material_name']}* — {item['topic']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{preview}",
            reply_markup=fav_item_kb(fav_id),
            parse_mode="Markdown",
        )

    elif data.startswith("regen_fav:"):
        fav_id = int(data.split(":")[1])
        item = get_favorite_item(fav_id, uid)
        if not item:
            await query.answer("⚠️ Табылмады", show_alert=True)
            return
        mtype = MType(item["material_type"])
        name_ru = _lookup_name_ru(item["section"], item["material_name"])
        context.user_data.update({
            "section": item["section"],
            "material_name": item["material_name"],
            "material_name_ru": name_ru,
            "material_type": mtype,
            "page": 0,
            "waiting_topic": True,
        })
        await query.edit_message_text(
            f"🔄 Тақырыпты жазыңыз:\n_Тема: {item['topic']}_",
            parse_mode="Markdown",
        )

    # ── PDF ──
    elif data.startswith("pdf:"):
        hist_id = int(data.split(":")[1])
        item = get_history_item(hist_id, uid)
        if not item or not item.get("result"):
            await query.answer("⚠️ Мазмұн табылмады", show_alert=True)
            return
        await query.answer("📄 PDF дайындалуда…")
        section_label = SECTIONS.get(item["section"], {}).get("label", item["section"])
        buf, fname, mime = pdf_gen.make_pdf(
            item["material_name"], section_label, item["topic"], item["result"]
        )
        await context.bot.send_document(
            chat_id=chat_id,
            document=buf,
            filename=fname,
            caption=f"📄 *{item['material_name']}* — {item['topic']}",
            parse_mode="Markdown",
        )

    elif data.startswith("pdf_fav:"):
        fav_id = int(data.split(":")[1])
        item = get_favorite_item(fav_id, uid)
        if not item or not item.get("result"):
            await query.answer("⚠️ Мазмұн табылмады", show_alert=True)
            return
        await query.answer("📄 PDF дайындалуда…")
        section_label = SECTIONS.get(item["section"], {}).get("label", item["section"])
        buf, fname, mime = pdf_gen.make_pdf(
            item["material_name"], section_label, item["topic"], item["result"]
        )
        await context.bot.send_document(
            chat_id=chat_id,
            document=buf,
            filename=fname,
            caption=f"📄 *{item['material_name']}* — {item['topic']}",
            parse_mode="Markdown",
        )

    # ── Share ──
    elif data.startswith("share:"):
        hist_id = int(data.split(":")[1])
        item = get_history_item(hist_id, uid)
        if not item or not item.get("result"):
            await query.answer("⚠️ Мазмұн табылмады", show_alert=True)
            return
        await query.answer("📤 Мазмұн жіберілуде…")
        preview = item["result"][:3500]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📤 *{item['material_name']}* — {item['topic']}\n"
                 f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                 f"{preview}\n\n"
                 f"_— MuzMugalim Bot_",
            parse_mode="Markdown",
        )

    # ── Admin panel ──
    elif data == "admin_panel":
        if uid != ADMIN_ID:
            await query.answer("⛔ Рұқсат жоқ", show_alert=True)
            return
        s = get_stats()
        plan_lines = "\n".join(
            f"  {_PLAN_ICON.get(p,'?')} {TARIFFS[p]['name']}: {c}"
            for p, c in s["plan_counts"].items() if c > 0
        )
        await query.edit_message_text(
            "━━━━━━━━━━━━━━━━━━━\n"
            "🛠️ *ADMIN PANEL*\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 *Статистика:*\n"
            f"👥 Барлық мұғалім: *{s['total_users']}*\n"
            f"💰 Ай табысы: *{s['revenue']:,} ₸*\n"
            f"📝 Бүгін жасалған: *{s['today_gen']}*\n\n"
            "📋 *Тарифтер:*\n"
            f"{plan_lines}\n\n"
            "━━━━━━━━━━━━━━━━━━━",
            reply_markup=admin_kb(),
            parse_mode="Markdown",
        )

    elif data == "admin:users":
        if uid != ADMIN_ID:
            await query.answer("⛔", show_alert=True)
            return
        users = get_all_users(20)
        lines = []
        for u in users:
            name = f"@{u['username']}" if u.get("username") else u.get("first_name", str(u["user_id"]))
            plan = TARIFFS.get(u.get("plan", "free"), {}).get("name", "?")
            lines.append(f"{name} | {plan} | 📝{u.get('text_total',0)} 🖼️{u.get('poster_total',0)} 🎵{u.get('music_total',0)}")
        text = f"👥 *Соңғы {len(users)} қолданушы:*\n\n" + "\n".join(lines) if lines else "Жоқ."
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=admin_kb())

    elif data == "admin:broadcast":
        if uid != ADMIN_ID:
            await query.answer("⛔", show_alert=True)
            return
        await query.edit_message_text(
            "📢 *Хабарлама жіберу / Рассылка*\n\n_Кімге жіберу?_",
            reply_markup=broadcast_kb(), parse_mode="Markdown",
        )

    elif data == "admin:fullstats":
        if uid != ADMIN_ID:
            await query.answer("⛔", show_alert=True)
            return
        s = get_stats()
        await query.edit_message_text(
            "📊 *Толық есеп / Полный отчёт*\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Барлық қолданушы: *{s['total_users']}*\n"
            f"💰 Ай табысы: *{s['revenue']:,} ₸*\n"
            f"📝 Бүгін жасалған: *{s['today_gen']}*\n\n"
            "📈 *Барлық уақытта:*\n"
            f"  📝 Мәтін: {s['text_total']}\n"
            f"  🖼️ Постер: {s['poster_total']}\n"
            f"  🎵 Музыка: {s['music_total']}\n\n"
            "📋 *Тарифтер:*\n"
            + "\n".join(
                f"  {_PLAN_ICON.get(p,'?')} {TARIFFS[p]['name']}: {c}"
                for p, c in s["plan_counts"].items()
            ),
            reply_markup=admin_kb(), parse_mode="Markdown",
        )

    elif data == "admin:giveplan":
        if uid != ADMIN_ID:
            await query.answer("⛔", show_alert=True)
            return
        await query.edit_message_text(
            "💰 *Тариф беру / Выдать тариф*\n\n"
            "_Пайдаланушыға тариф беру үшін:_\n\n"
            "`/activate <user_id> <plan> [days]`\n\n"
            "_Мысалы: /activate 123456789 premium 30_",
            parse_mode="Markdown",
            reply_markup=admin_kb(),
        )

    # ── Broadcast ──
    elif data.startswith("broadcast:"):
        if uid != ADMIN_ID:
            await query.answer("⛔", show_alert=True)
            return
        plan_filter = data.split(":")[1]
        context.user_data["broadcast_filter"] = plan_filter
        context.user_data["waiting_broadcast"] = True
        filter_name = {
            "all": "Барлығы / Все",
            "basic": "Базалық",
            "standard": "Стандарт",
            "premium": "Премиум",
            "full": "Толық / Полный",
        }.get(plan_filter, plan_filter)
        await query.edit_message_text(
            f"📢 *{filter_name}* қолданушыларға хабарлама жіберіледі.\n\n"
            "_Хабарлама мәтінін жазыңыз:_\n"
            "_Введите текст сообщения:_",
            parse_mode="Markdown",
        )


# ─── Payment helper ───────────────────────────────────────────────────────────

async def _show_payment(query, update, context, plan: str):
    tariff = TARIFFS[plan]
    name = tariff["name"]
    price = tariff["price"]
    plan_icon = {"basic": "🥉", "standard": "🥈", "premium": "🥇", "full": "👑"}.get(plan, "💎")

    features = {
        "basic":    "📝 Мәтін — шексіз\n   └ Мектеп: 21 + Балабақша: 27 материал",
        "standard": "📝 Мәтін — шексіз\n   └ 🖼️ Постер — 30/ай\n   └ 📁 Портфолио",
        "premium":  "📝 Мәтін — шексіз\n   └ 🖼️ Постер — 50/ай\n   └ 🎵 Музыка MP3 — 10/ай",
        "full":     "📝🖼️🎵 Барлығы + Сценарийлер + Конкурс",
    }

    text = (
        f"{plan_icon} *{name} тарифі*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Сома: *{price:,} ₸/ай*\n\n"
        f"✅ Мүмкіндіктер:\n"
        f"   └ {features.get(plan, '')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 *Төлем нұсқаулығы:*\n\n"
        f"💳 *Kaspi аударым:*\n"
        f"   📱 Номер: *8 707 307 88 74*\n"
        f"   👤 Алтынай\n"
        f"   💰 Сома: *{price:,} ₸*\n\n"
        f"📸 *Төлем скриншотын жіберіңіз:*\n"
        f"   👇 Төмендегі кнопканы басыңыз\n\n"
        f"✅ Тариф *1–2 сағат* ішінде белсендіріледі"
    )
    await query.edit_message_text(text, reply_markup=payment_kb(plan), parse_mode="Markdown")

    tg_user = update.effective_user
    uname = f"@{tg_user.username}" if tg_user.username else tg_user.first_name
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"💳 *Жаңа төлем сұранысы*\n\n"
            f"👤 {uname} (`{tg_user.id}`)\n"
            f"📦 Тариф: *{name}* — {price:,} ₸\n\n"
            f"Белсендіру: `/activate {tg_user.id} {plan}`",
            parse_mode="Markdown",
        )
    except Exception:
        pass


# ─── List helper ──────────────────────────────────────────────────────────────

async def _show_list(query, section: str, page: int, user_plan: str):
    materials = SECTIONS[section]["materials"]
    total = len(materials)
    label = SECTIONS[section]["label"]
    plan_name = TARIFFS.get(user_plan, {}).get("name", "Тегін")
    plan_icon = _PLAN_ICON.get(user_plan, "🆓")
    await query.edit_message_text(
        f"{label}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{plan_icon} Тариф: *{plan_name}*  •  📦 {total} материал\n\n"
        f"👇 *Не жасайық?*\n"
        f"_✅ қолжетімді  •  🔒 тариф жоғарылату керек_",
        reply_markup=material_list_kb(section, page, user_plan),
        parse_mode="Markdown",
    )


# ─── Text / generation handler ────────────────────────────────────────────────

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    uid = update.effective_user.id

    # ── Broadcast mode (admin) ──
    if context.user_data.get("waiting_broadcast") and uid == ADMIN_ID:
        plan_filter = context.user_data.pop("broadcast_filter", "all")
        context.user_data["waiting_broadcast"] = False
        text = update.message.text.strip()
        user_ids = get_users_for_broadcast(plan_filter)
        msg = await update.message.reply_text(
            f"📢 *{len(user_ids)}* қолданушыға жіберілуде…", parse_mode="Markdown"
        )
        sent = failed = 0
        for target_id in user_ids:
            try:
                await context.bot.send_message(target_id, text)
                sent += 1
            except Exception:
                failed += 1
        await msg.edit_text(
            f"✅ Жіберілді: *{sent}*\n❌ Сәтсіз: *{failed}*",
            parse_mode="Markdown",
        )
        return

    if not context.user_data.get("waiting_topic"):
        await update.message.reply_text("👇 Материал таңдаңыз:", reply_markup=main_menu_kb())
        return

    section = context.user_data.get("section", "mektep")
    material_name = context.user_data.get("material_name", "")
    material_name_ru = context.user_data.get("material_name_ru", "")
    material_type = context.user_data.get("material_type", MType.TEXT)
    topic = update.message.text.strip()
    context.user_data["waiting_topic"] = False
    page = context.user_data.get("page", 0)

    allowed, reason = check_quota(uid, material_type)
    if not allowed and reason not in ("no_poster_access", "no_music_access"):
        await update.message.reply_text(reason, reply_markup=upgrade_kb())
        return

    if material_type == MType.TEXT:
        msg = await update.message.reply_text(
            f"⚙️ *{material_name}* жасалуда…\n_Gemini 2.5 Flash жұмыс істеп жатыр_",
            parse_mode="Markdown",
        )
        try:
            lang = context.user_data.get("lang", "kz")
            result = await generators.gen_text(section, material_name, topic, lang, name_ru=material_name_ru)
            record_usage(uid, "text")
            hist_id = save_history(uid, section, material_name, "text", topic, result)
            await msg.delete()
            for part in generators.split_long_message(result):
                await update.message.reply_text(part)
            usage_line = _usage_line(uid, "text")
            done_text = (
                f"✅ *{material_name}* дайын!\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                + (f"{usage_line}\n" if usage_line else "")
                + "👇 Не жасайық?"
            )
            await update.message.reply_text(
                done_text,
                reply_markup=result_kb(hist_id, section, page),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("gen_text error: %s", e, exc_info=True)
            await msg.delete()
            await update.message.reply_text(
                f"⚠️ Қате шықты, қайталап көріңіз.\n`{e}`",
                reply_markup=main_menu_kb(), parse_mode="Markdown",
            )

    elif material_type == MType.POSTER:
        msg = await update.message.reply_text(
            "🎨 *Постер* жасалуда…\n_Imagen 4 Fast суреттеп жатыр (15–30 сек)_",
            parse_mode="Markdown",
        )
        try:
            img_bytes = await generators.gen_poster(section, material_name, topic)
            record_usage(uid, "poster")
            hist_id = save_history(uid, section, material_name, "poster", topic, "[poster]")
            await msg.delete()
            await update.message.reply_photo(
                photo=io.BytesIO(img_bytes),
                caption=f"🖼️ *{material_name}* — {topic}",
                parse_mode="Markdown",
            )
            usage_line = _usage_line(uid, "poster")
            done_text = (
                "✅ *Постер дайын!*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                + (f"{usage_line}\n" if usage_line else "")
                + "👇 Не жасайық?"
            )
            await update.message.reply_text(
                done_text,
                reply_markup=result_kb(hist_id, section, page),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("gen_poster error: %s", e, exc_info=True)
            await msg.delete()
            await update.message.reply_text(
                f"⚠️ Постер жасалмады, қайталаңыз.\n`{e}`",
                reply_markup=main_menu_kb(), parse_mode="Markdown",
            )

    elif material_type == MType.MUSIC:
        msg = await update.message.reply_text(
            "🎼 *Музыка* жасалуда…\n_Suno AI компоциялап жатыр (30–60 сек)_",
            parse_mode="Markdown",
        )
        try:
            mp3_bytes, title = await generators.gen_music(section, material_name, topic)
            record_usage(uid, "music")
            hist_id = save_history(uid, section, material_name, "music", topic, f"[audio:{title}]")
            await msg.delete()
            await update.message.reply_audio(
                audio=io.BytesIO(mp3_bytes),
                title=title,
                filename=f"{title}.mp3",
                caption=f"🎵 *{material_name}* — {topic}",
                parse_mode="Markdown",
            )
            usage_line = _usage_line(uid, "music")
            done_text = (
                "✅ *Музыка дайын!*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                + (f"{usage_line}\n" if usage_line else "")
                + "👇 Не жасайық?"
            )
            await update.message.reply_text(
                done_text,
                reply_markup=result_kb(hist_id, section, page),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("gen_music error: %s", e, exc_info=True)
            await msg.delete()
            await update.message.reply_text(
                f"⚠️ Музыка жасалмады, қайталаңыз.\n`{e}`",
                reply_markup=main_menu_kb(), parse_mode="Markdown",
            )
