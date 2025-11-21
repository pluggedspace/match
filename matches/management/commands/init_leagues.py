# matches/management/commands/init_leagues.py
from django.core.management.base import BaseCommand
from matches.models import League, Fixture, Match, Prediction
from django.db import transaction

class Command(BaseCommand):
    help = "Initialize default leagues and backfill existing data"

    DEFAULT_LEAGUES = [
        {"name": "Premier League", "code": "EPL", "country": "England"},
        {"name": "La Liga", "code": "LALIGA", "country": "Spain"},
        {"name": "Serie A", "code": "SERIEA", "country": "Italy"},
        {"name": "Bundesliga", "code": "BUNDES", "country": "Germany"},
        {"name": "Ligue 1", "code": "LIGUE1", "country": "France"},
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Initializing default leagues..."))
        leagues = {}
        for data in self.DEFAULT_LEAGUES:
            league, created = League.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "country": data["country"]
                }
            )
            leagues[data["code"]] = league
            msg = "Created" if created else "Existing"
            self.stdout.write(f"  {msg}: {league.name}")

        # Choose a default (EPL) to backfill
        default_league = leagues["EPL"]

        self.stdout.write(self.style.WARNING("Backfilling existing fixtures, matches, and predictions..."))

        fixture_count = Fixture.objects.filter(league__isnull=True).update(league=default_league)
        match_count = Match.objects.filter(league__isnull=True).update(league=default_league)
        pred_count = Prediction.objects.filter(league__isnull=True).update(league=default_league)

        self.stdout.write(self.style.SUCCESS(
            f"Backfill complete: Fixtures={fixture_count}, Matches={match_count}, Predictions={pred_count}"
        ))

        self.stdout.write(self.style.SUCCESS("✅ League initialization complete."))