import os
import logging

from telegram.error import Conflict

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


async def _error_handler(update, context):
    if isinstance(context.error, Conflict):
        logging.getLogger(__name__).warning(
            "Conflict: басқа бот нұсқасы сол токенмен жұмыс істеп тұр (getUpdates)"
        )
        return
    logging.getLogger(__name__).error("Unhandled error", exc_info=context.error)


async def _reminder_job(context):
    """Daily job: notify users whose tariff expires in 3 days."""
    from storage import get_expiring_users

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


async def _expiry_job(context):
    """Hourly job: remove access of users whose tariff has expired."""
    from storage import downgrade_expired_users

    for uid in downgrade_expired_users():
        try:
            await context.bot.send_message(
                uid,
                "ℹ️ *Тариф мерзімі аяқталды.*\n\n"
                "Жалғастыру үшін тарифты жаңартыңыз.\n"
                "Жаңарту үшін @muzmugalim-ге хабарласыңыз.\n\n"
                "ℹ️ *Срок тарифа истёк.*\n"
                "Для продолжения продлите тариф.\n"
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

    app.add_error_handler(_error_handler)

    # Callbacks & messages
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Expiry jobs: reminder once a day, access removal every hour
    if app.job_queue:
        app.job_queue.run_repeating(_reminder_job, interval=86400, first=60)
        app.job_queue.run_repeating(_expiry_job, interval=3600, first=30)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
