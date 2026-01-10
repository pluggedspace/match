from django.core.management.base import BaseCommand
from matches.models import Match

class Command(BaseCommand):
    help = "Check score data in Match table"

    def handle(self, *args, **options):
        total_matches = Match.objects.count()
        matches_with_scores = Match.objects.filter(
            home_score__isnull=False,
            away_score__isnull=False
        ).count()
        
        matches_without_scores = total_matches - matches_with_scores
        
        self.stdout.write(f"Total matches: {total_matches}")
        self.stdout.write(f"Matches WITH scores: {matches_with_scores}")
        self.stdout.write(f"Matches WITHOUT scores: {matches_without_scores}")
        
        # Sample a match without scores
        self.stdout.write("\n=== Sample matches WITHOUT scores ===")
        no_score_matches = Match.objects.filter(
            home_score__isnull=True
        )[:5]
        
        for m in no_score_matches:
            self.stdout.write(
                f"{m.date.date()}: {m.home_team} vs {m.away_team} | "
                f"home_score={m.home_score}, away_score={m.away_score}, result={m.result}"
            )
        
        # Sample a match WITH scores (if any)
        self.stdout.write("\n=== Sample matches WITH scores ===")
        with_score_matches = Match.objects.filter(
            home_score__isnull=False,
            away_score__isnull=False
        )[:5]
        
        if with_score_matches.exists():
            for m in with_score_matches:
                self.stdout.write(
                    f"{m.date.date()}: {m.home_team} vs {m.away_team} | "
                    f"home_score={m.home_score}, away_score={m.away_score}, result={m.result}"
                )
        else:
            self.stdout.write("No matches with scores found!")
