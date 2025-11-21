# matches/services/gameweek.py
from django.utils.timezone import now
from matches.models import Gameweek, Fixture

def get_current_gameweek():
    today = now()
    return Gameweek.objects.filter(start_date__lte=today, end_date__gte=today).first()

def get_fixtures_for_gameweek(gameweek: Gameweek):
    """Return all fixtures whose date falls inside the gameweek."""
    return Fixture.objects.filter(date__range=(gameweek.start_date, gameweek.end_date)) \
                          .select_related("home_team", "away_team") \
                          .prefetch_related("prediction_set")