from django.core.management.base import BaseCommand
from matches.models import Match, Team
from matches.api_client import get_past_fixtures
from django.utils.dateparse import parse_datetime
from datetime import datetime
from django.db import IntegrityError


class Command(BaseCommand):
    help = "Sync past finished matches into Match model"

    def handle(self, *args, **kwargs):
        league_id = 39  # EPL
        season = 2025
        league_name = "Premier League"
        past_fixtures = get_past_fixtures(league_id=league_id, season=season, count=50)

        for item in past_fixtures['response']:
            try:
                fixture = item['fixture']
                teams = item['teams']
                score = item['score']

                fixture_id = fixture['id']
                date_str = fixture['date']
                status = fixture['status']['short']

                # Skip if match is not finished
                if status != 'FT':
                    self.stdout.write(f"⏭️ Skipping fixture {fixture_id} - status: {status}")
                    continue

                home_team_api_id = teams['home']['id']
                away_team_api_id = teams['away']['id']
                home_team_name = teams['home']['name']
                away_team_name = teams['away']['name']

                # Use your existing canonical method
                home_team = Team.get_or_create_canonical(
                    name=home_team_name,
                    country="England",
                    api_id=home_team_api_id
                )

                away_team = Team.get_or_create_canonical(
                    name=away_team_name,
                    country="England", 
                    api_id=away_team_api_id
                )

                home_goals = score['fulltime']['home']
                away_goals = score['fulltime']['away']

                if home_goals is None or away_goals is None:
                    self.stdout.write(f"⏭️ Skipping fixture {fixture_id} - no score data")
                    continue

                # Parse date properly
                try:
                    date = parse_datetime(date_str)
                    if not date:
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    self.stderr.write(f"❌ Could not parse date: {date_str}")
                    continue

                # Determine match result
                if home_goals > away_goals:
                    result = 'win'
                elif home_goals < away_goals:
                    result = 'loss'
                else:
                    result = 'draw'

                # Use the API fixture_id as primary, with fallback
                if not fixture_id:
                    fixture_id = Match.canonical_fixture_id(home_team, away_team, league_name, str(season), date)

                match, created = Match.objects.update_or_create(
                    fixture_id=fixture_id,
                    defaults={
                        'home_team': home_team,
                        'away_team': away_team,
                        'league': league_name,
                        'season': str(season),
                        'date': date,
                        'home_score': home_goals,
                        'away_score': away_goals,
                        'result': result
                    }
                )

                if created:
                    self.stdout.write(f"✅ Added match {home_team} vs {away_team} ({home_goals}-{away_goals})")
                else:
                    self.stdout.write(f"🔁 Updated match {home_team} vs {away_team} ({home_goals}-{away_goals})")

            except IntegrityError as e:
                self.stderr.write(f"❌ Integrity error for fixture {fixture_id}: {e}")
                continue
            except Exception as e:
                self.stderr.write(f"❌ Unexpected error for fixture {fixture_id}: {e}")
                continue