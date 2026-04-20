import os
import logging
from dotenv import load_dotenv
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN орнатылмаған")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY орнатылмаған")

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Сен — MuzMugalim Bot, Қазақстандағы музыка мұғалімдеріне арналған AI көмекші.
Қазақша жауап бер. Мұғалімдерге сабақ материалдары жасауға көмектес."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏫 Мектеп 📚", callback_data="mektep")],
        [InlineKeyboardButton("🎪 Балабақша 🎈", callback_data="balabaqsha")],
        [InlineKeyboardButton("💰 Тариф 💳", callback_data="tarif")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎵 Сәлем, ұстаз! 🎶 MuzMugalim Bot-қа қош келдіңіз! 🌟\n\n"
        "Не жасауға көмек керек? 🤔",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "mektep":
        await query.edit_message_text(
            "🏫 Мектеп бөлімі!\n\n"
            "Не жасайын?\n"
            "📝 Көрнекілік\n"
            "📋 Тест\n"
            "📄 ҚМЖ/КТЖ\n"
            "🎼 Диктант\n\n"
            "Тақырып жазыңыз!"
        )
    elif query.data == "balabaqsha":
        await query.edit_message_text(
            "🎪 Балабақша бөлімі!\n\n"
            "Не жасайын?\n"
            "📅 Жоспар\n"
            "🎭 Сценарий\n"
            "🎮 Ойын\n\n"
            "Тақырып жазыңыз!"
        )
    elif query.data == "tarif":
        await query.edit_message_text(
            "💰 Тариф:\n\n"
            "🥉 Базалық — 3 990 ₸/ай\n"
            "🥈 Стандарт — 5 990 ₸/ай\n"
            "🥇 Премиум — 10 990 ₸/ай\n"
            "👑 Толық — 14 990 ₸/ай\n\n"
            "📞 Жазылу үшін: @muzmugalim"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text("⏳ Жасап жатырмын...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=SYSTEM_PROMPT + "\n\nМұғалім сұрады: " + user_message
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Gemini қатесі: {e}", exc_info=True)
        await update.message.reply_text(f"⚠️ Қате болды: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()