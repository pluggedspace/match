# telegrambot/handlers/help.py
from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "⚽ *MatchBot - AI Match Predictions*\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n\n"
    "🔮 *PREDICTIONS*\n"
    "• `/predict <Team A> vs <Team B>`\n"
    "  _Example: /predict Arsenal vs Manchester United_\n\n"
    "📅 *FIXTURES & SCHEDULES*\n"
    "• `/nextmatch` - Next match globally\n"
    "• `/nextmatch <League/Team>` - Filter by context\n"
    "  _Examples:_\n"
    "  _/nextmatch EPL_\n"
    "  _/nextmatch Arsenal_\n"
    "  _/nextmatch England_\n\n"
    "• `/gameweek` - Current gameweek fixtures\n"
    "• `/gameweek <League>` - Filter by league\n"
    "  _Example: /gameweek Champions League_\n\n"
    "• `/upcoming <League/Competition>` - Next 10 predictions\n"
    "  _Example: /upcoming La Liga_\n\n"
    "💎 *SUBSCRIPTION*\n"
    "• `/subscribe <email>` - Upgrade to Premium\n"
    "• `/start` - Check your subscription status\n\n"
    "❓ *HELP*\n"
    "• `/help` - Show this help message\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 _Just type any command above to get started!_"
)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_TEXT, 
        parse_mode="Markdown"
    )