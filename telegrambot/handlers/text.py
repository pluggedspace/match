from telegram import Update
from telegram.ext import ContextTypes
from .predict import predict_command
from .utils import parse_teams_from_text

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages, trying to parse as prediction requests."""
    text = update.message.text
    team_a, team_b = parse_teams_from_text(text)
    if team_a and team_b:
        context.args = [team_a, "vs", team_b]
        await predict_command(update, context)
    else:
        await update.message.reply_text(
            "💬 *Not sure what you meant!*\n\n"
            "Try using a command:\n"
            "• `/predict Arsenal vs Chelsea`\n"
            "• `/nextmatch EPL`\n"
            "• `/upcoming Champions League`\n\n"
            "Or type `/help` to see all commands.",
            parse_mode="Markdown"
        )