# bot/handlers/upcoming.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import Q
from matches.models import Prediction, League, Competition, Country
from .utils import get_or_create_telegram_user

logger = logging.getLogger(__name__)

@sync_to_async
def get_upcoming_predictions(query_text=None, limit=10):
    """Fetch upcoming predictions, optionally filtered by league/comp/country."""
    base_query = Prediction.objects.filter(
        fixture__date__gte=timezone.now()
    ).select_related(
        "fixture__home_team", "fixture__away_team", "fixture__league", "fixture__competition"
    )
    
    if query_text:
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
    
    return list(base_query.order_by("fixture__date")[:limit])

async def upcoming_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /upcoming command to show upcoming predictions."""
    try:
        user = await sync_to_async(get_or_create_telegram_user)(update.effective_user)
        
        # Get query text from arguments
        query_text = " ".join(context.args) if context.args else None
        
        if not query_text:
            await update.message.reply_text(
                "❌ *Missing League/Competition*\n\n"
                "Please specify what you want to see:\n\n"
                "📝 *Usage:*\n"
                "`/upcoming <League/Competition/Country>`\n\n"
                "✨ *Examples:*\n"
                "• `/upcoming EPL`\n"
                "• `/upcoming Champions League`\n"
                "• `/upcoming England`\n\n"
                "💡 _Try `/help` for more commands!_",
                parse_mode="Markdown"
            )
            return
        
        predictions = await get_upcoming_predictions(query_text, limit=10)

        if not predictions:
            await update.message.reply_text(
                f"❌ *No upcoming predictions found*\n\n"
                f"No fixtures available for: *'{query_text}'*\n\n"
                f"💡 *Suggestions:*\n"
                f"• Check spelling\n"
                f"• Try a different league name\n"
                f"• Use `/help` to see all commands",
                parse_mode="Markdown"
            )
            return

        title = f"📈 *UPCOMING PREDICTIONS*\n{query_text.title()}"
        msg_lines = [title, "\n━━━━━━━━━━━━━━━━━━━━━\n"]

        for i, pred in enumerate(predictions, 1):
            fixture = pred.fixture
            
            # Format date and time
            match_date = fixture.date.strftime('%b %d')
            match_time = fixture.date.strftime('%H:%M')
            
            # Confidence indicator (pred.confidence is stored as 0-1 float)
            confidence_emoji = "🟢" if pred.confidence >= 0.7 else "🟡" if pred.confidence >= 0.5 else "🔴"
            
            line = (
                f"\n{i}. *{fixture.home_team}* vs *{fixture.away_team}*\n"
                f"   📅 {match_date} at {match_time}\n"
                f"   {confidence_emoji} Prediction: {pred.result_pred.upper()} ({pred.confidence * 100:.0f}%)"
            )
            msg_lines.append(line)

        msg_lines.append("\n\n━━━━━━━━━━━━━━━━━━━━━")
        msg_lines.append("\n💡 _Use /predict to get detailed analysis_")



        await update.message.reply_text(
            "\n".join(msg_lines),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in upcoming_command: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ *Oops! Something went wrong*\n\n"
            "We couldn't fetch upcoming predictions. Please try again.\n\n"
            "Use `/help` for more commands.",
            parse_mode="Markdown"
        )
