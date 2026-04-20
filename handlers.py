import logging

from telegram import Update
from telegram.ext import ContextTypes

import ai
from config import SECTIONS, TARIFFS, ADMIN_ID
from keyboards import main_menu_kb, material_list_kb, back_to_list_kb, tarif_kb
from storage import ensure_user, check_quota, record_usage, activate_plan

logger = logging.getLogger(__name__)

TARIF_TEXT = (
    "💰 *Тариф жоспарлары*\n\n"
    "🥉 *Базалық* — 3 990 ₸/ай\n"
    "   • 50 материал/ай\n\n"
    "🥈 *Стандарт* — 5 990 ₸/ай\n"
    "   • 150 материал/ай\n\n"
    "🥇 *Премиум* — 10 990 ₸/ай\n"
    "   • 500 материал/ай\n\n"
    "👑 *Толық* — 14 990 ₸/ай\n"
    "   • Шексіз материал\n\n"
    "📞 Жазылу үшін: @muzmugalim\n"
    "🎁 Тегін: алғашқы 3 сұраныс"
)

MAIN_MENU_TEXT = (
    "🎵 *MuzMugalim Bot-қа қош келдіңіз!*\n\n"
    "Музыка мұғалімдеріне арналған AI көмекші.\n"
    "Бөлімді таңдаңыз:"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
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
        user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id сан болуы керек.")
        return
    plan = args[1].lower()
    if activate_plan(user_id, plan):
        await update.message.reply_text(
            f"✅ {user_id} пайдаланушысына *{plan}* тарифі белсендірілді.",
            parse_mode="Markdown"
        )
    else:
        valid = ", ".join(TARIFFS.keys())
        await update.message.reply_text(f"❌ Белгісіз тариф. Қолжетімділер: {valid}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_kb(),
            parse_mode="Markdown"
        )

    elif data == "tarif":
        await query.edit_message_text(
            TARIF_TEXT,
            reply_markup=tarif_kb(),
            parse_mode="Markdown"
        )

    elif data.startswith("section:"):
        section = data.split(":")[1]
        context.user_data["section"] = section
        context.user_data["page"] = 0
        context.user_data["waiting_topic"] = False
        await _show_material_list(query, section, 0)

    elif data.startswith("page:"):
        _, section, page_str = data.split(":")
        page = int(page_str)
        context.user_data["section"] = section
        context.user_data["page"] = page
        context.user_data["waiting_topic"] = False
        await _show_material_list(query, section, page)

    elif data.startswith("material:"):
        _, section, idx_str = data.split(":")
        idx = int(idx_str)
        page = context.user_data.get("page", 0)
        material_name = SECTIONS[section]["materials"][idx]
        context.user_data["section"] = section
        context.user_data["material_idx"] = idx
        context.user_data["material_name"] = material_name
        context.user_data["waiting_topic"] = True
        await query.edit_message_text(
            f"📝 *{material_name}*\n\n"
            f"Тақырыпты жазыңыз (мысалы: «Домбыра», «Моцарт», «Ән жанры»):",
            reply_markup=back_to_list_kb(section, page),
            parse_mode="Markdown"
        )


async def _show_material_list(query, section: str, page: int):
    materials = SECTIONS[section]["materials"]
    total = len(materials)
    total_pages = (total + 8 - 1) // 8
    label = SECTIONS[section]["label"]
    await query.edit_message_text(
        f"{label} бөлімі\n"
        f"Бет: {page + 1}/{total_pages} • Барлығы: {total} материал\n\n"
        f"Материал түрін таңдаңыз:",
        reply_markup=material_list_kb(section, page)
    )


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)

    if not context.user_data.get("waiting_topic"):
        await update.message.reply_text(
            "👇 Материал таңдаңыз:",
            reply_markup=main_menu_kb()
        )
        return

    user_id = update.effective_user.id
    allowed, reason = check_quota(user_id)
    if not allowed:
        context.user_data["waiting_topic"] = False
        await update.message.reply_text(reason, reply_markup=main_menu_kb())
        return

    section = context.user_data.get("section", "mektep")
    material_name = context.user_data.get("material_name", "")
    topic = update.message.text.strip()

    context.user_data["waiting_topic"] = False

    await update.message.reply_text("⏳ Жасап жатырмын, күте тұрыңыз...")

    try:
        result = await ai.generate(section, material_name, topic)
        record_usage(user_id)

        parts = ai.split_long_message(result)
        for part in parts:
            await update.message.reply_text(part)

        await update.message.reply_text(
            "✅ Дайын! Тағы бір материал керек пе?",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"AI қатесі: {e}", exc_info=True)
        await update.message.reply_text(
            f"⚠️ Қате болды: {e}\n\nҚайталап көріңіз.",
            reply_markup=main_menu_kb()
        )
