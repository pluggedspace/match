from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.db.models import Q
from matches.models import Match, Fixture
from matches.logic.feature_training import calculate_form
import logging

logger = logging.getLogger(__name__)

@sync_to_async
def _get_fixture_and_form(fixture_id: str):
    """Load fixture and compute form for both teams using training utilities."""
    fixture = (
        Fixture.objects
        .select_related("home_team", "away_team")
        .get(id=fixture_id)
    )
    # calculate_form uses past Match data; pass fixture date for correct cutoff
    home_form = calculate_form(fixture.home_team, date=fixture.date)
    away_form = calculate_form(fixture.away_team, date=fixture.date)
    return fixture, home_form, away_form


@sync_to_async
def _get_h2h_stats(fixture_id: str, limit: int = 10):
    """Compute simple head-to-head stats between the two teams using Match history."""
    fixture = (
        Fixture.objects
        .select_related("home_team", "away_team")
        .get(id=fixture_id)
    )
    home = fixture.home_team
    away = fixture.away_team

    qs = (
        Match.objects
        .filter(
            Q(home_team=home, away_team=away) | Q(home_team=away, away_team=home),
            result__isnull=False,
        )
        .order_by("-date")[:limit]
    )

    total = qs.count()
    if total == 0:
        return fixture, {"total": 0}

    home_wins = draws = away_wins = 0
    recent_results = []

    for m in qs:
        if m.home_team == home:
            result = m.result
        else:
            # invert perspective when stored with teams swapped
            result = {"win": "loss", "loss": "win", "draw": "draw"}.get(m.result, m.result)

        if result == "win":
            home_wins += 1
            symbol = "W"
        elif result == "draw":
            draws += 1
            symbol = "D"
        else:
            away_wins += 1
            symbol = "L"

        recent_results.append(symbol)

    stats = {
        "total": total,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "recent": "".join(recent_results),
    }
    return fixture, stats


async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if ":" not in data:
        logger.warning(f"Invalid callback data: {data}")
        await query.answer("Invalid action.", show_alert=True)
        return

    action, fixture_id = data.split(":", 1)

    try:
        if action == "form":
            fixture, home_form, away_form = await _get_fixture_and_form(fixture_id)
            await query.edit_message_text(
                f"📊 Team Form (last matches)\n\n"
                f"{fixture.home_team}: {home_form * 100:.0f}%\n"
                f"{fixture.away_team}: {away_form * 100:.0f}%"
            )
        elif action == "h2h":
            fixture, stats = await _get_h2h_stats(fixture_id)
            if not stats.get("total"):
                await query.edit_message_text(
                    f"⚔️ Head-to-head\n\n"
                    f"No historical meetings found for\n"
                    f"{fixture.home_team} vs {fixture.away_team}."
                )
                return

            await query.edit_message_text(
                f"⚔️ Head-to-head (last {stats['total']} matches)\n\n"
                f"{fixture.home_team} wins: {stats['home_wins']}\n"
                f"Draws: {stats['draws']}\n"
                f"{fixture.away_team} wins: {stats['away_wins']}\n\n"
                f"Recent: {stats['recent']} (W=Home win, D=Draw, L=Home loss)"
            )
        else:
            logger.warning(f"Unknown inline action: {action}")
            await query.answer("Unknown action.", show_alert=True)
    except Fixture.DoesNotExist:
        await query.edit_message_text("Fixture not found.")
    except Exception as e:
        logger.error(f"Error handling inline callback '{data}': {e}", exc_info=True)
        await query.edit_message_text("An error occurred while processing this request.")