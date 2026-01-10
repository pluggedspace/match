# bot/handlers/gameweek.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.db.models import Q
from matches.services.gameweek import get_current_gameweek, get_fixtures_for_gameweek
from matches.models import League, Competition
from .utils import get_or_create_telegram_user

logger = logging.getLogger(__name__)

@sync_to_async
def fetch_gameweek_data(query_text=None):
    gw = get_current_gameweek()
    if not gw:
        return None, []

    fixtures = get_fixtures_for_gameweek(gw)
    
    # Apply filtering if query_text provided
    if query_text:
        # Try to match League
        league = League.objects.filter(
            Q(name__icontains=query_text) | Q(code__icontains=query_text)
        ).first()
        if league:
            fixtures = fixtures.filter(league=league)
        else:
            # Try to match Competition
            comp = Competition.objects.filter(
                Q(name__icontains=query_text) | Q(code__icontains=query_text)
            ).first()
            if comp:
                fixtures = fixtures.filter(competition=comp)
    
    fixtures = list(fixtures)  # force QuerySet evaluation

    # Prefetch predictions to avoid lazy DB calls in async context
    for f in fixtures:
        f.predictions = list(f.prediction_set.all())

    return gw, fixtures


async def gameweek_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = await sync_to_async(get_or_create_telegram_user)(update.effective_user)
        
        # Get query text from arguments
        query_text = " ".join(context.args) if context.args else None
        
        gw, fixtures = await fetch_gameweek_data(query_text)
        if not gw:
            await update.message.reply_text(
                "⚠️ *No active Gameweek found*\n\n"
                "There are currently no scheduled gameweeks.\n\n"
                "Use `/help` for more commands.",
                parse_mode="Markdown"
            )
            return

        if not fixtures:
            msg = f"⚠️ *No fixtures found for Gameweek {gw.number}*"
            if query_text:
                msg += f" matching *'{query_text}'*"
            msg += "\n\nTry a different league or use `/help` for more commands."
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        title = f"📊 *GAMEWEEK {gw.number} FIXTURES*"
        if query_text:
            title += f" - {query_text.title()}"
        
        msg_lines = [title, "\n━━━━━━━━━━━━━━━━━━━━━\n"]

        for i, f in enumerate(fixtures[:15], 1):  # Limit to 15 to avoid message length issues
            pred = f.predictions[0] if f.predictions else None
            
            # Format date
            match_date = f.date.strftime('%b %d, %H:%M')
            
            line = f"\n{i}. *{f.home_team}* vs *{f.away_team}*\n"
            line += f"   📅 {match_date}"

            if pred:
                confidence_emoji = "🟢" if pred.confidence >= 70 else "🟡" if pred.confidence >= 50 else "🔴"
                line += f"\n   {confidence_emoji} Prediction: {pred.result_pred.upper()} ({pred.confidence:.0f}%)"

            msg_lines.append(line)

        if len(fixtures) > 15:
            msg_lines.append(f"\n\n_...and {len(fixtures) - 15} more fixtures_")

        msg_lines.append("\n\n━━━━━━━━━━━━━━━━━━━━━")
        


        await update.message.reply_text(
            "\n".join(msg_lines),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in gameweek_command: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ *Oops! Something went wrong*\n\n"
            "We couldn't fetch gameweek fixtures. Please try again.\n\n"
            "Use `/help` for more commands.",
            parse_mode="Markdown"
        )