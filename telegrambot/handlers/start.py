# telegrambot/start.py
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from matches.models import UserSubscription
from .utils import get_or_create_telegram_user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await sync_to_async(get_or_create_telegram_user)(tg_user)

    # Step 1: Check UserSubscription directly
    subscription = await sync_to_async(UserSubscription.objects.filter(user=user).first)()

    if subscription and subscription.status.lower() == "success":
        await update.message.reply_text(
            f"👋 Welcome back, {tg_user.first_name}!\n"
            "✅ You have an active *MatchBot Premium* subscription.\n\n"
            "You can now use /predict, /nextmatch, or /gameweek.",
            parse_mode="Markdown",
        )
        return

    # Step 2: Handle free users
    await update.message.reply_text(
        f"👋 Welcome {tg_user.first_name}!\n"
        "You're currently on the *Free Plan* (limited predictions).\n\n"
        "Upgrade to *MatchBot Premium* for full access to advanced match predictions and insights.\n\n"
        "To upgrade, type:\n`/subscribe your@email.com`",
        parse_mode="Markdown",
    )