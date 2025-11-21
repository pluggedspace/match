from telegram import Update
from telegram.ext import ContextTypes
from matches.models import Match
from matches.logic.feature_training import calculate_form
import logging

logger = logging.getLogger(__name__)

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if ":" not in data:
        logger.warning(f"Invalid callback data: {data}")
        await query.answer("Invalid action.", show_alert=True)
        return

    action, match_id = data.split(":", 1)

    try:
        match = Match.objects.get(id=match_id)
    except Match.DoesNotExist:
        await query.edit_message_text("Match not found.")
        return

    if action == "form":
        form_home = calculate_form(match.home_team)
        form_away = calculate_form(match.away_team)
        await query.edit_message_text(
            f"📊 Form:\n\n"
            f"{match.home_team}: {form_home}\n"
            f"{match.away_team}: {form_away}"
        )
    elif action == "h2h":
        await query.edit_message_text("⚔️ Head-to-head data coming soon.")