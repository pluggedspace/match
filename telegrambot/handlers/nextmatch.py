import logging
from asgiref.sync import sync_to_async
from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from matches.models import Prediction
from .utils import get_or_create_telegram_user  # Import the helper function

logger = logging.getLogger(__name__)

@sync_to_async
def get_next_prediction():
    """Fetch the next upcoming prediction from the database."""
    return (
        Prediction.objects
        .filter(fixture__date__gte=timezone.now())
        .select_related("fixture", "fixture__home_team", "fixture__away_team")
        .order_by("fixture__date")
        .first()
    )

async def nextmatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /nextmatch command."""
    try:
        # Wrap the synchronous function with sync_to_async
        user = await sync_to_async(get_or_create_telegram_user)(update.effective_user)
        
        pred = await get_next_prediction()

        if not pred:
            await update.message.reply_text("❌ No upcoming matches with predictions found.")
            return

        fixture = pred.fixture
        msg = (
            f"📅 *Next Match Prediction*\n"
            f"{fixture.home_team} vs {fixture.away_team}\n"
            f"🗓 {fixture.date.strftime('%Y-%m-%d %H:%M')}\n"
            f"🔮 Prediction: {pred.result_pred.upper()}\n"
            f"💰 Fair Odds: "
            f"Home: {pred.fair_odds_home or 'N/A'} | "
            f"Draw: {pred.fair_odds_draw or 'N/A'} | "
            f"Away: {pred.fair_odds_away or 'N/A'}\n"
            f"📈 Confidence: {pred.confidence or 'N/A'}%"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Form", callback_data=f"form:{fixture.id}")],
            [InlineKeyboardButton("⚔️ H2H", callback_data=f"h2h:{fixture.id}")]
        ])

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in nextmatch command: {e}")
        await update.message.reply_text("⚠️ An error occurred while fetching the next match prediction.")