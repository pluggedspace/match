from django.core.management.base import BaseCommand
from matches.models import Fixture, Team, League
from matches.api_client import get_fixtures, get_league_id_by_name_and_country
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = "Sync upcoming fixtures from API for a specific league (lookup by name and country)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--league-name",
            type=str,
            required=True,
            help="League name (e.g., 'Premier League', 'La Liga')"
        )
        parser.add_argument(
            "--country",
            type=str,
            required=True,
            help="Country name (e.g., 'England', 'Spain')"
        )
        parser.add_argument(
            "--season",
            type=int,
            default=2023,
            help="Season year (e.g., 2023)"
        )
        parser.add_argument(
            "--next",
            type=int,
            default=20,
            help="Number of upcoming fixtures to fetch"
        )

    def handle(self, *args, **options):
        league_name = options["league_name"]
        country = options["country"]
        season = options["season"]
        next_n = options["next"]

        # Get or create League instance first
        league_instance, league_created = League.objects.get_or_create(
            name=league_name,
            defaults={
                'country': country,
                'code': league_name.upper().replace(' ', '_')
            }
        )
        
        if league_created:
            self.stdout.write(f"Created new league: {league_name}")

        league_id = get_league_id_by_name_and_country(league_name, country, season)
        if not league_id:
            self.stdout.write(self.style.ERROR(
                f"League '{league_name}' in '{country}' not found for season {season}"
            ))
            return

        fixtures_data = get_fixtures(league_id=league_id, season=season, next_n=next_n)

        for item in fixtures_data['response']:
            fixture_info = item['fixture']
            home_info = item['teams']['home']
            away_info = item['teams']['away']

            # Handle home team - lookup by (name, country)
            home_team, home_created = Team.objects.get_or_create(
                name=home_info['name'],
                country=country,
                defaults={'api_id': home_info['id']}
            )
            
            # If team exists but has no api_id or different api_id, update it
            if not home_created and (not home_team.api_id or home_team.api_id != home_info['id']):
                home_team.api_id = home_info['id']
                home_team.save()
                self.stdout.write(f"Updated {home_team.name} api_id to {home_info['id']}")

            # Handle away team - lookup by (name, country)
            away_team, away_created = Team.objects.get_or_create(
                name=away_info['name'],
                country=country,
                defaults={'api_id': away_info['id']}
            )
            
            # If team exists but has no api_id or different api_id, update it
            if not away_created and (not away_team.api_id or away_team.api_id != away_info['id']):
                away_team.api_id = away_info['id']
                away_team.save()
                self.stdout.write(f"Updated {away_team.name} api_id to {away_info['id']}")

            # Use League instance instead of string
            fixture, created = Fixture.objects.update_or_create(
                id=fixture_info['id'],
                defaults={
                    'date': parse_datetime(fixture_info['date']),
                    'status': fixture_info['status']['long'],
                    'league': league_instance,  # Use League instance here
                    'season': str(season),
                    'home_team': home_team,
                    'away_team': away_team
                }
            )

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} fixture: {home_team.name} vs {away_team.name}")