from django.core.management.base import BaseCommand
from matches.models import Match, Team
from django.db.models import Q

class Command(BaseCommand):
    help = "Test raw query to verify database access"

    def handle(self, *args, **options):
        # Get Aston Villa
        team = Team.objects.get(id=14)
        self.stdout.write(f"Testing queries for: {team.name} (ID: {team.id})")
        
        # Test 1: Simple query
        self.stdout.write("\n=== Test 1: Simple team filter ===")
        simple = Match.objects.filter(home_team=team)
        self.stdout.write(f"Matches as home team: {simple.count()}")
        
        # Test 2: Q object OR
        self.stdout.write("\n=== Test 2: Q object (home OR away) ===")
        q_or = Match.objects.filter(Q(home_team=team) | Q(away_team=team))
        self.stdout.write(f"Matches as home OR away: {q_or.count()}")
        
        # Test 3: Q object with AND for scores
        self.stdout.write("\n=== Test 3: Q object with score filters ===")
        query = Q(home_team=team) | Q(away_team=team)
        query &= Q(home_score__isnull=False) & Q(away_score__isnull=False)
        q_and = Match.objects.filter(query)
        self.stdout.write(f"Matches with scores: {q_and.count()}")
        
        if q_and.exists():
            self.stdout.write("\nFirst 3 matches:")
            for m in q_and.order_by('-date')[:3]:
                self.stdout.write(f"  {m.date.date()}: {m.home_team} vs {m.away_team} ({m.home_score}-{m.away_score})")
        
        # Test 4: With date filter
        self.stdout.write("\n=== Test 4: With date filter (before 2025-11-30) ===")
        from datetime import datetime
        from django.utils import timezone
        
        date_filter = timezone.make_aware(datetime(2025, 11, 30, 14, 5, 0))
        query_date = query & Q(date__lt=date_filter)
        q_date = Match.objects.filter(query_date)
        self.stdout.write(f"Matches before {date_filter}: {q_date.count()}")
        
        if q_date.exists():
            self.stdout.write("\nFirst 3 matches:")
            for m in q_date.order_by('-date')[:3]:
                self.stdout.write(f"  {m.date.date()}: {m.home_team} vs {m.away_team} ({m.home_score}-{m.away_score})")
