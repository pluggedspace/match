# handlers/predict.py
import logging
from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from django.db.models import Q

from matches.models import Prediction, UserPrediction
from .utils import get_or_create_telegram_user   # helper we created earlier

logger = logging.getLogger(__name__)

@sync_to_async
def get_prediction(team_a: str, team_b: str):
    """Query the Prediction model for saved results (handles both orders)."""
    return (
        Prediction.objects
        .filter(
            # Either home vs away...
            (
                Q(fixture__home_team__name__icontains=team_a) &
                Q(fixture__away_team__name__icontains=team_b)
            )
            # ...or away vs home
            | (
                Q(fixture__home_team__name__icontains=team_b) &
                Q(fixture__away_team__name__icontains=team_a)
            )
        )
        .select_related("fixture__home_team", "fixture__away_team", "fixture__league", "fixture__competition")
        .first()
    )

@sync_to_async
def save_user_prediction(user, fixture, predicted_result):
    """Save or update a UserPrediction for this fixture."""
    UserPrediction.objects.update_or_create(
        user=user,
        fixture=fixture,
        defaults={"predicted_result": predicted_result}
    )

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /predict command by fetching from Prediction model and logging user request."""
    try:
        telegram_user = update.effective_user
        user = await sync_to_async(get_or_create_telegram_user)(telegram_user)

        text = " ".join(context.args)

        if " vs " not in text.lower():
            await update.message.reply_text(
                "❌ *Invalid Format*\n\n"
                "Please use: `/predict <Team A> vs <Team B>`\n\n"
                "📝 *Example:*\n"
                "`/predict Arsenal vs Manchester United`\n\n"
                "💡 _Tip: Make sure to include 'vs' between team names!_\n\n"
                "Try: `/nextmatch` or `/help` for more commands.",
                parse_mode="Markdown"
            )
            return

        team_a, team_b = [t.strip() for t in text.split(" vs ", 1)]

        pred = await get_prediction(team_a, team_b)

        if not pred:
            await update.message.reply_text(
                f"❌ *Prediction Not Found*\n\n"
                f"No prediction available for:\n"
                f"_{team_a}_ vs _{team_b}_\n\n"
                f"💡 *Suggestions:*\n"
                f"• Check team name spelling\n"
                f"• Try `/nextmatch` for upcoming matches\n"
                f"• Use `/help` to see all commands",
                parse_mode="Markdown"
            )
            return

        # Save this user's prediction request
        await save_user_prediction(user, pred.fixture, pred.result_pred)

        # Build context string
        context_parts = []
        if pred.fixture.competition:
            context_parts.append(f"🏆 {pred.fixture.competition.name}")
        elif pred.fixture.league:
            context_parts.append(f"⚽ {pred.fixture.league.name}")
        
        context_str = " | ".join(context_parts) if context_parts else ""
        
        # Build confidence indicator (pred.confidence is stored as 0-1 float)
        confidence_emoji = "🟢" if pred.confidence >= 0.7 else "🟡" if pred.confidence >= 0.5 else "🔴"

        msg = (
            f"🔮 *MATCH PREDICTION*\n\n"
            f"⚽ *{pred.fixture.home_team}* vs *{pred.fixture.away_team}*\n"
            + (f"{context_str}\n" if context_str else "")
            + f"\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            + f"📊 *Predicted Outcome:* {pred.result_pred.upper()}\n"
            + f"{confidence_emoji} *Confidence:* {pred.confidence * 100:.1f}%\n"
            + f"📈 *Goal Difference:* {pred.goal_diff:+.1f}\n\n"
            + f"💰 *Fair Odds:*\n"
            + f"  • Home Win: {pred.fair_odds_home}\n"
            + f"  • Draw: {pred.fair_odds_draw}\n"
            + f"  • Away Win: {pred.fair_odds_away}\n\n"
            + f"━━━━━━━━━━━━━━━━━━━━━"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Team Form", callback_data=f"form:{pred.fixture.id}"),
                InlineKeyboardButton("⚔️ Head to Head", callback_data=f"h2h:{pred.fixture.id}")
            ],

        ])

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in predict_command: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ *Oops! Something went wrong*\n\n"
            "We couldn't fetch the prediction. Please try again or contact support.\n\n"
            "Use `/help` to see available commands.",
            parse_mode="Markdown"
        )