# telegrambot/start.py
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from matches.models import UserSubscription
from .utils import get_or_create_telegram_user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await sync_to_async(get_or_create_telegram_user)(tg_user)

    # Check UserSubscription
    subscription = await sync_to_async(UserSubscription.objects.filter(user=user).first)()

    if subscription and subscription.status.lower() == "success":
        await update.message.reply_text(
            f"👋 *Welcome back, {tg_user.first_name}!*\n\n"
            "✅ You have an active *MatchBot Premium* subscription.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 *Quick Commands:*\n"
            "• `/predict Arsenal vs Chelsea`\n"
            "• `/nextmatch EPL`\n"
            "• `/upcoming Champions League`\n"
            "• `/gameweek`\n\n"
            "Type `/help` for all commands.\n\n"
            "💡 _Get instant predictions and match insights!_",
            parse_mode="Markdown"
        )
        return

    # Handle free users
    await update.message.reply_text(
        f"👋 *Welcome {tg_user.first_name}!*\n\n"
        "You're currently on the *Free Plan* (limited predictions).\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💎 *Upgrade to MatchBot Premium*\n"
        "Get unlimited access to:\n"
        "  ✓ AI-powered match predictions\n"
        "  ✓ Real-time odds analysis\n"
        "  ✓ Detailed team statistics\n"
        "  ✓ Upcoming fixtures & gameweeks\n\n"
        "To upgrade, type:\n"
        "`/subscribe your@email.com`\n\n"
        "Type `/help` to see all available commands.",
        parse_mode="Markdown"
    )