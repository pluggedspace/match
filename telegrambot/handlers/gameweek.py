# bot/handlers/gameweek.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from matches.services.gameweek import get_current_gameweek, get_fixtures_for_gameweek
from .utils import get_or_create_telegram_user  # Import the helper function

logger = logging.getLogger(__name__)

# --------------------------
# Sync wrapper to fetch data
# --------------------------
@sync_to_async
def fetch_gameweek_data():
    gw = get_current_gameweek()
    if not gw:
        return None, []

    fixtures = list(get_fixtures_for_gameweek(gw))  # force QuerySet evaluation

    # Prefetch predictions to avoid lazy DB calls in async context
    for f in fixtures:
        f.predictions = list(f.prediction_set.all())

    return gw, fixtures


# --------------------------
# Async Telegram command
# --------------------------
async def gameweek_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Wrap the synchronous function with sync_to_async
        user = await sync_to_async(get_or_create_telegram_user)(update.effective_user)
        
        gw, fixtures = await fetch_gameweek_data()
        if not gw:
            await update.message.reply_text("⚠️ No active Gameweek found.")
            return

        msg_lines = [f"📅 *Gameweek {gw.number} Fixtures*"]

        for f in fixtures:
            pred = f.predictions[0] if f.predictions else None
            line = f"• {f.home_team} vs {f.away_team} ({f.date:%d %b %H:%M})"

            if pred:
                line += f" → {pred.result_pred.upper()} ({pred.confidence:.1f}%)"

            msg_lines.append(line)

        await update.message.reply_text(
            "\n".join(msg_lines),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in gameweek_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Couldn't fetch gameweek fixtures.")


# --------------------------
# Optional: Inline buttons
# --------------------------
# You can add buttons for H2H, Form, or Predictions if you like:
# keyboard = InlineKeyboardMarkup([
#     [InlineKeyboardButton("📊 Form", callback_data=f"form:{f.id}")],
#     [InlineKeyboardButton("⚔️ H2H", callback_data=f"h2h:{f.id}")]
# ])
# Then use reply_markup=keyboard in reply_text