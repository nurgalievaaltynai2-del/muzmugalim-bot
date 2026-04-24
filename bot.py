import os
import logging

from dotenv import load_dotenv

load_dotenv()

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TARIFFS
from handlers import (
    start_command,
    help_command,
    tariff_command,
    profile_command,
    history_command,
    favorites_command,
    activate_command,
    stats_command,
    users_command,
    admin_command,
    broadcast_command,
    button_handler,
    text_message_handler,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def _expiry_job(context):
    """Daily job: notify users expiring in 3 days, downgrade expired ones."""
    from storage import get_expiring_users, downgrade_expired_users

    for user in get_expiring_users(days=3):
        try:
            plan_name = TARIFFS[user["plan"]]["name"]
            exp_date = user["expires_at"][:10]
            from datetime import datetime
            exp = datetime.strptime(exp_date, "%Y-%m-%d")
            exp_str = exp.strftime("%d.%m.%Y")
            await context.bot.send_message(
                user["user_id"],
                f"⚠️ *Тариф мерзімі аяқталуға 3 күн қалды!*\n\n"
                f"📦 Тариф: *{plan_name}*\n"
                f"📅 Мерзімі: *{exp_str}*\n\n"
                f"Жалғастыру үшін @muzmugalim-ге хабарласыңыз.\n\n"
                f"⚠️ *До окончания тарифа осталось 3 дня!*\n"
                f"Для продления обратитесь @muzmugalim",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    for uid in downgrade_expired_users():
        try:
            await context.bot.send_message(
                uid,
                "ℹ️ *Тариф мерзімі аяқталды.*\n\n"
                "Тарифіңіз *Базалық*-қа ауысты.\n"
                "Жаңарту үшін @muzmugalim-ге хабарласыңыз.\n\n"
                "ℹ️ *Срок тарифа истёк.*\n"
                "Ваш тариф переключён на *Базовый*.\n"
                "Для продления обратитесь @muzmugalim",
                parse_mode="Markdown",
            )
        except Exception:
            pass


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN орнатылмаған")

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start",     start_command))
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(CommandHandler("tariff",    tariff_command))
    app.add_handler(CommandHandler("profile",   profile_command))
    app.add_handler(CommandHandler("history",   history_command))
    app.add_handler(CommandHandler("favorites", favorites_command))
    app.add_handler(CommandHandler("activate",  activate_command))
    app.add_handler(CommandHandler("stats",     stats_command))
    app.add_handler(CommandHandler("users",     users_command))
    app.add_handler(CommandHandler("admin",     admin_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))

    # Callbacks & messages
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Daily expiry check job (runs every 24 hours)
    if app.job_queue:
        app.job_queue.run_repeating(_expiry_job, interval=86400, first=60)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
