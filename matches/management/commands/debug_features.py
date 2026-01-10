from django.core.management.base import BaseCommand
from matches.models import Match, Fixture, Team
from matches.logic.feature_training import get_recent_matches, calculate_form, calculate_strength
from django.db.models import Q

class Command(BaseCommand):
    help = "Deep dive into feature extraction for specific teams"

    def handle(self, *args, **options):
        # Get a fixture team
        fixture = Fixture.objects.filter(league_id=1).first()
        if not fixture:
            self.stdout.write(self.style.ERROR("No fixtures found"))
            return
        
        team = fixture.home_team
        fixture_date = fixture.date
        
        self.stdout.write(f"Testing feature extraction for: {team.name} (ID: {team.id})")
        self.stdout.write(f"Fixture date: {fixture_date}")
        
        # Test get_recent_matches WITHOUT date filter
        self.stdout.write("\n=== Testing get_recent_matches WITHOUT date filter ===")
        matches_no_date = get_recent_matches(team, limit=20, date=None)
        self.stdout.write(f"Found {matches_no_date.count()} matches")
        
        if matches_no_date.exists():
            for m in matches_no_date[:3]:
                self.stdout.write(f"  {m.date.date()}: {m.home_team} vs {m.away_team} ({m.home_score}-{m.away_score})")
        
        # Test get_recent_matches WITH date filter
        self.stdout.write(f"\n=== Testing get_recent_matches WITH date={fixture_date} ===")
        matches_with_date = get_recent_matches(team, limit=20, date=fixture_date)
        self.stdout.write(f"Found {matches_with_date.count()} matches")
        
        if matches_with_date.exists():
            for m in matches_with_date[:3]:
                self.stdout.write(f"  {m.date.date()}: {m.home_team} vs {m.away_team} ({m.home_score}-{m.away_score})")
        else:
            self.stdout.write(self.style.WARNING("  No matches found!"))
            
            # Check if there are ANY matches for this team
            all_matches = Match.objects.filter(
                Q(home_team=team) | Q(away_team=team)
            ).order_by('-date')
            
            self.stdout.write(f"\n  Total matches in DB for {team.name}: {all_matches.count()}")
            if all_matches.exists():
                latest = all_matches.first()
                self.stdout.write(f"  Latest match date: {latest.date}")
                self.stdout.write(f"  Fixture date: {fixture_date}")
                self.stdout.write(f"  Latest match BEFORE fixture? {latest.date < fixture_date}")
        
        # Test feature calculation
        self.stdout.write("\n=== Testing Feature Calculation ===")
        form = calculate_form(team, date=fixture_date)
        strength = calculate_strength(team, date=fixture_date)
        
        self.stdout.write(f"Form: {form}")
        self.stdout.write(f"Strength: {strength}")
        
        # Check different team (one that showed 0 features)
        self.stdout.write("\n" + "="*50)
        self.stdout.write("=== Checking Crystal Palace specifically ===")
        
        cp_teams = Team.objects.filter(name__icontains="Crystal Palace")
        self.stdout.write(f"Found {cp_teams.count()} teams matching 'Crystal Palace':")
        for t in cp_teams:
            self.stdout.write(f"  - {t.name} (ID: {t.id}, Country: {t.country})")
            
            matches = Match.objects.filter(
                Q(home_team=t) | Q(away_team=t)
            )
            self.stdout.write(f"    Total matches: {matches.count()}")
            
            if matches.exists():
                for m in matches[:2]:
                    self.stdout.write(f"      {m.date.date()}: {m.home_team} vs {m.away_team}")
