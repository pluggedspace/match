from django.core.management.base import BaseCommand
from matches.models import Match, Fixture, Team
from django.db.models import Q, Count

class Command(BaseCommand):
    help = "Check data consistency between Match and Fixture tables"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=== CHECKING DATA CONSISTENCY ===\n"))
        
        # Check Match league distribution
        self.stdout.write("Match table - League distribution:")
        match_leagues = Match.objects.values('league_id', 'league__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for ml in match_leagues:
            league_name = ml['league__name'] or 'NULL'
            self.stdout.write(f"  League ID {ml['league_id']}: {league_name} - {ml['count']} matches")
        
        # Check Fixture league distribution
        self.stdout.write("\nFixture table - League distribution:")
        fixture_leagues = Fixture.objects.values('league_id', 'league__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for fl in fixture_leagues:
            league_name = fl['league__name'] or 'NULL'
            self.stdout.write(f"  League ID {fl['league_id']}: {league_name} - {fl['count']} fixtures")
        
        # Check team overlap
        self.stdout.write("\n=== CHECKING TEAM OVERLAP ===")
        
        # Get sample fixture team
        sample_fixture = Fixture.objects.filter(league_id=1).first()
        if sample_fixture:
            team = sample_fixture.home_team
            self.stdout.write(f"\nSample team from Fixture: {team.name} (ID: {team.id})")
            
            # Check if this team exists in Match table
            match_count_all = Match.objects.filter(
                Q(home_team=team) | Q(away_team=team)
            ).count()
            
            match_count_league1 = Match.objects.filter(
                Q(home_team=team) | Q(away_team=team),
                league_id=1
            ).count()
            
            self.stdout.write(f"  Total matches for this team: {match_count_all}")
            self.stdout.write(f"  Matches with league_id=1: {match_count_league1}")
            
            # Show a few matches for this team
            matches = Match.objects.filter(
                Q(home_team=team) | Q(away_team=team)
            ).select_related('league').order_by('-date')[:5]
            
            if matches:
                self.stdout.write(f"\n  Recent matches for {team.name}:")
                for m in matches:
                    league_str = f"League: {m.league.name if m.league else 'None'} (ID: {m.league_id})"
                    self.stdout.write(f"    {m.date.date()} - {league_str}")
            else:
                self.stdout.write(self.style.WARNING(f"  No matches found for {team.name}"))
        
        # Check if Match table uses league at all
        self.stdout.write("\n=== MATCH TABLE LEAGUE USAGE ===")
        total_matches = Match.objects.count()
        matches_with_league = Match.objects.exclude(league__isnull=True).count()
        matches_without_league = total_matches - matches_with_league
        
        self.stdout.write(f"Total matches: {total_matches}")
        self.stdout.write(f"Matches WITH league set: {matches_with_league}")
        self.stdout.write(f"Matches WITHOUT league (NULL): {matches_without_league}")
