import io
import logging

from telegram import Update
from telegram.ext import ContextTypes

import generators
from config import SECTIONS, TARIFFS, PLAN_RANK, ADMIN_ID, MType
from keyboards import main_menu_kb, material_list_kb, back_to_list_kb, tarif_kb, upgrade_kb
from storage import (
    ensure_user, check_quota, record_usage,
    activate_plan, get_stats, get_all_users,
)

logger = logging.getLogger(__name__)

MAIN_MENU_TEXT = (
    "🎵 *MuzMugalim Bot-қа қош келдіңіз!*\n\n"
    "Музыка мұғалімдеріне арналған AI көмекші.\n"
    "Бөлімді таңдаңыз:"
)

TARIF_TEXT = (
    "💰 *Тариф жоспарлары*\n\n"
    "🥉 *Базалық — 3 990 ₸/ай*\n"
    "   ✅ Шексіз мәтін материалдары\n"
    "   ✅ 22 мектеп + 27 балабақша материалы\n\n"
    "🥈 *Стандарт — 5 990 ₸/ай*\n"
    "   ✅ Базалықтың бәрі\n"
    "   ✅ 🖼️ Постер генерация — 30/ай\n"
    "   ✅ Портфолио\n\n"
    "🥇 *Премиум — 10 990 ₸/ай*\n"
    "   ✅ Стандарттың бәрі\n"
    "   ✅ 🖼️ Постер — 50/ай\n"
    "   ✅ 🎵 Музыка MP3 — 10/ай\n"
    "   ✅ Рефлексия, Дифф.тапсырма\n\n"
    "👑 *Толық — 14 990 ₸/ай*\n"
    "   ✅ 78 мүмкіндік\n"
    "   ✅ 🖼️ Постер — шексіз\n"
    "   ✅ 🎵 Музыка — шексіз\n"
    "   ✅ Барлық сценарийлер мен мерекелер\n\n"
    "─────────────────────\n"
    "💳 *Kaspi QR арқылы төлем*\n"
    "📞 Жазылу үшін: @muzmugalim\n"
    "🎁 Тегін: алғашқы 3 сұраныс"
)


# ─── Command handlers ─────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )


async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Формат: /activate <user_id> <plan>")
        return
    try:
        uid = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id сан болуы керек.")
        return
    plan = args[1].lower()
    if activate_plan(uid, plan):
        await update.message.reply_text(
            f"✅ `{uid}` пайдаланушысына *{plan}* тарифі белсендірілді.",
            parse_mode="Markdown",
        )
    else:
        valid = ", ".join(TARIFFS.keys())
        await update.message.reply_text(f"❌ Белгісіз тариф. Қолжетімдісі: {valid}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    s = get_stats()
    plan_lines = "\n".join(
        f"  {TARIFFS[p]['name']}: {c}" for p, c in s["plan_counts"].items() if c > 0
    )
    text = (
        f"📊 *Статистика*\n\n"
        f"👥 Барлық қолданушылар: {s['total_users']}\n\n"
        f"📋 *Тарифтер:*\n{plan_lines}\n\n"
        f"📈 *Осы айда:*\n"
        f"  📝 Мәтін: {s['text_total']}\n"
        f"  🖼️ Постер: {s['poster_total']}\n"
        f"  🎵 Музыка: {s['music_total']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Рұқсат жоқ.")
        return
    users = get_all_users(20)
    if not users:
        await update.message.reply_text("Қолданушылар жоқ.")
        return
    lines = []
    for u in users:
        uname = f"@{u['username']}" if u.get("username") else u.get("first_name", str(u["user_id"]))
        plan = TARIFFS.get(u.get("plan", "free"), {}).get("name", "?")
        lines.append(
            f"{uname} | {plan} | "
            f"📝{u.get('text_used', 0)} 🖼️{u.get('poster_used', 0)} 🎵{u.get('music_used', 0)}"
        )
    await update.message.reply_text(
        f"👥 *Соңғы {len(users)} қолданушы:*\n\n" + "\n".join(lines),
        parse_mode="Markdown",
    )


# ─── Callback handler ─────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            MAIN_MENU_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown"
        )

    elif data == "tarif":
        await query.edit_message_text(
            TARIF_TEXT, reply_markup=tarif_kb(), parse_mode="Markdown"
        )

    elif data.startswith("section:"):
        section = data.split(":")[1]
        context.user_data.update({"section": section, "page": 0, "waiting_topic": False})
        user = ensure_user(update.effective_user)
        await _show_material_list(query, section, 0, user["plan"])

    elif data.startswith("page:"):
        _, section, page_str = data.split(":")
        page = int(page_str)
        context.user_data.update({"section": section, "page": page, "waiting_topic": False})
        user = ensure_user(update.effective_user)
        await _show_material_list(query, section, page, user["plan"])

    elif data.startswith("material:"):
        _, section, idx_str = data.split(":")
        idx = int(idx_str)
        mat = SECTIONS[section]["materials"][idx]
        page = context.user_data.get("page", 0)
        user = ensure_user(update.effective_user)
        user_rank = PLAN_RANK.get(user["plan"], 0)

        # Access check
        if PLAN_RANK[mat.min_plan] > user_rank:
            needed = TARIFFS[mat.min_plan]["name"]
            await query.edit_message_text(
                f"🔒 *{mat.name}* материалы *{needed}* тарифінен қолжетімді.\n\n"
                f"Жазылу үшін @muzmugalim-ге хабарласыңыз.",
                reply_markup=upgrade_kb(),
                parse_mode="Markdown",
            )
            return

        # Quota check
        allowed, reason = check_quota(update.effective_user.id, mat.mtype)
        if not allowed:
            if reason == "no_poster_access":
                needed = TARIFFS["standard"]["name"]
                await query.edit_message_text(
                    f"🔒 Постер генерациясы *{needed}* тарифінен қолжетімді.\n\n"
                    "Жазылу үшін @muzmugalim-ге хабарласыңыз.",
                    reply_markup=upgrade_kb(),
                    parse_mode="Markdown",
                )
            elif reason == "no_music_access":
                needed = TARIFFS["premium"]["name"]
                await query.edit_message_text(
                    f"🔒 Музыка MP3 генерациясы *{needed}* тарифінен қолжетімді.\n\n"
                    "Жазылу үшін @muzmugalim-ге хабарласыңыз.",
                    reply_markup=upgrade_kb(),
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    reason, reply_markup=upgrade_kb(), parse_mode="Markdown"
                )
            return

        # Ask for topic
        context.user_data.update({
            "section": section,
            "material_idx": idx,
            "material_name": mat.name,
            "material_type": mat.mtype,
            "page": page,
            "waiting_topic": True,
        })

        type_prompts = {
            MType.TEXT: "Тақырыпты жазыңыз (мысалы: «Домбыра», «Моцарт», «Ән жанры»):",
            MType.POSTER: "Постер тақырыбын жазыңыз (мысалы: «Наурыз», «Домбыра»):",
            MType.MUSIC: "Музыка тақырыбын жазыңыз (мысалы: «Көктем», «Балалар би»):",
        }
        type_icons = {MType.TEXT: "📝", MType.POSTER: "🖼️", MType.MUSIC: "🎵"}

        await query.edit_message_text(
            f"{type_icons[mat.mtype]} *{mat.name}*\n\n"
            f"{type_prompts[mat.mtype]}",
            reply_markup=back_to_list_kb(section, page),
            parse_mode="Markdown",
        )


async def _show_material_list(query, section: str, page: int, user_plan: str):
    materials = SECTIONS[section]["materials"]
    total = len(materials)
    total_pages = (total + 8 - 1) // 8
    label = SECTIONS[section]["label"]
    plan_name = TARIFFS.get(user_plan, {}).get("name", "Тегін")
    await query.edit_message_text(
        f"{label} бөлімі\n"
        f"Бет: {page + 1}/{total_pages} • Барлығы: {total} материал\n"
        f"Тарифіңіз: {plan_name}\n\n"
        f"Материал түрін таңдаңыз:\n"
        f"_(🔒 — жоғарырақ тариф қажет)_",
        reply_markup=material_list_kb(section, page, user_plan),
        parse_mode="Markdown",
    )


# ─── Message handler ──────────────────────────────────────────────────────────

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)

    if not context.user_data.get("waiting_topic"):
        await update.message.reply_text(
            "👇 Материал таңдаңыз:", reply_markup=main_menu_kb()
        )
        return

    user_id = update.effective_user.id
    section = context.user_data.get("section", "mektep")
    material_name = context.user_data.get("material_name", "")
    material_type = context.user_data.get("material_type", MType.TEXT)
    topic = update.message.text.strip()
    context.user_data["waiting_topic"] = False

    # Re-check quota at generation time
    allowed, reason = check_quota(user_id, material_type)
    if not allowed and reason not in ("no_poster_access", "no_music_access"):
        await update.message.reply_text(reason, reply_markup=upgrade_kb())
        return

    if material_type == MType.TEXT:
        await update.message.reply_text("⏳ Мәтін жасап жатырмын...")
        try:
            result = await generators.gen_text(section, material_name, topic)
            record_usage(user_id, "text")
            for part in generators.split_long_message(result):
                await update.message.reply_text(part)
            await update.message.reply_text("✅ Дайын!", reply_markup=main_menu_kb())
        except Exception as e:
            logger.error(f"gen_text error: {e}", exc_info=True)
            await update.message.reply_text(
                f"⚠️ Қате: {e}\n\nҚайталап көріңіз.", reply_markup=main_menu_kb()
            )

    elif material_type == MType.POSTER:
        await update.message.reply_text("⏳ Постер жасап жатырмын (15-30 сек)...")
        try:
            img_bytes = await generators.gen_poster(section, material_name, topic)
            record_usage(user_id, "poster")
            await update.message.reply_photo(
                photo=io.BytesIO(img_bytes),
                caption=f"🖼️ {material_name}: {topic}",
            )
            await update.message.reply_text("✅ Постер дайын!", reply_markup=main_menu_kb())
        except Exception as e:
            logger.error(f"gen_poster error: {e}", exc_info=True)
            await update.message.reply_text(
                f"⚠️ Постер жасау қатесі: {e}\n\nҚайталап көріңіз.", reply_markup=main_menu_kb()
            )

    elif material_type == MType.MUSIC:
        await update.message.reply_text("⏳ Музыка жасап жатырмын (30-60 сек)...")
        try:
            mp3_bytes, title = await generators.gen_music(section, material_name, topic)
            record_usage(user_id, "music")
            await update.message.reply_audio(
                audio=io.BytesIO(mp3_bytes),
                title=title,
                filename=f"{title}.mp3",
                caption=f"🎵 {material_name}: {topic}",
            )
            await update.message.reply_text("✅ Музыка дайын!", reply_markup=main_menu_kb())
        except Exception as e:
            logger.error(f"gen_music error: {e}", exc_info=True)
            await update.message.reply_text(
                f"⚠️ Музыка жасау қатесі: {e}\n\nҚайталап көріңіз.", reply_markup=main_menu_kb()
            )
