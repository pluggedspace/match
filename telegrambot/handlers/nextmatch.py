import logging
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import Q
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from matches.models import Prediction, Team, League, Competition, Country
from .utils import get_or_create_telegram_user

logger = logging.getLogger(__name__)

@sync_to_async
def get_next_prediction(query_text=None):
    """Fetch the next upcoming prediction from the database, optionally filtered by context."""
    base_query = Prediction.objects.filter(
        fixture__date__gte=timezone.now()
    ).select_related(
        "fixture__home_team", "fixture__away_team", "fixture__league", "fixture__competition"
    )
    
    if query_text:
        # Try to match Team
        team = Team.objects.filter(name__icontains=query_text).first()
        if team:
            base_query = base_query.filter(
                Q(fixture__home_team=team) | Q(fixture__away_team=team)
            )
        else:
            # Try to match League
            league = League.objects.filter(
                Q(name__icontains=query_text) | Q(code__icontains=query_text)
            ).first()
            if league:
                base_query = base_query.filter(fixture__league=league)
            else:
                # Try to match Competition
                comp = Competition.objects.filter(
                    Q(name__icontains=query_text) | Q(code__icontains=query_text)
                ).first()
                if comp:
                    base_query = base_query.filter(fixture__competition=comp)
                else:
                    # Try to match Country
                    country = Country.objects.filter(
                        Q(name__icontains=query_text) | Q(code__icontains=query_text)
                    ).first()
                    if country:
                        base_query = base_query.filter(
                            Q(fixture__home_team__country_link=country) | 
                            Q(fixture__away_team__country_link=country)
                        )
    
    return base_query.order_by("fixture__date").first()

async def nextmatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /nextmatch command with optional filtering."""
    try:
        user = await sync_to_async(get_or_create_telegram_user)(update.effective_user)
        
        # Get query text from arguments
        query_text = " ".join(context.args) if context.args else None
        
        pred = await get_next_prediction(query_text)

        if not pred:
            msg = "❌ *No upcoming matches found*"
            if query_text:
                msg += f" for *'{query_text}'*"
            msg += "\n\n💡 Try `/help` to see all available commands."
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        fixture = pred.fixture
        
        # Build context string
        context_parts = []
        if fixture.competition:
            context_parts.append(f"🏆 {fixture.competition.name}")
        elif fixture.league:
            context_parts.append(f"⚽ {fixture.league.name}")
        
        context_str = " | ".join(context_parts)
        
        # Build confidence indicator (pred.confidence is stored as 0-1 float)
        confidence_emoji = "🟢" if pred.confidence >= 0.7 else "🟡" if pred.confidence >= 0.5 else "🔴"
        
        # Format date
        match_date = fixture.date.strftime('%A, %B %d')
        match_time = fixture.date.strftime('%H:%M')
        
        msg = (
            f"📅 *NEXT MATCH PREDICTION*\n\n"
            f"⚽ *{fixture.home_team}* vs *{fixture.away_team}*\n"
            + (f"{context_str}\n" if context_str else "")
            + f"\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            + f"🗓 *Date:* {match_date}\n"
            + f"⏰ *Time:* {match_time}\n\n"
            + f"📊 *Predicted Outcome:* {pred.result_pred.upper()}\n"
            + f"{confidence_emoji} *Confidence:* {pred.confidence * 100:.1f}%\n\n"
            + f"💰 *Fair Odds:*\n"
            + f"  • Home Win: {pred.fair_odds_home or 'N/A'}\n"
            + f"  • Draw: {pred.fair_odds_draw or 'N/A'}\n"
            + f"  • Away Win: {pred.fair_odds_away or 'N/A'}\n\n"
            + f"━━━━━━━━━━━━━━━━━━━━━"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Team Form", callback_data=f"form:{fixture.id}"),
                InlineKeyboardButton("⚔️ Head to Head", callback_data=f"h2h:{fixture.id}")
            ],

        ])

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in nextmatch command: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ *Oops! Something went wrong*\n\n"
            "We couldn't fetch the next match. Please try again.\n\n"
            "Use `/help` for more commands.",
            parse_mode="Markdown"
        )