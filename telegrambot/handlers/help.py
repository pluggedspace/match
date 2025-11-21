# telegrambot/handlers/help.py
from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "⚽ *MatchBot Commands*\n\n"
    "/start - Link your Telegram account and view your plan status\n"
    "/predict - Get Premium AI match prediction (e.g. Manchester United vs Liverpool)\n"
    "/nextmatch - View upcoming match predictions\n"
    "/gameweek - See current gameweek fixtures and results\n"
    "/subscribe - Upgrade to MatchBot Premium for full access\n"
    "/help - View all available MatchBot commands\n"
)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")