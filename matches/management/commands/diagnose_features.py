from django.core.management.base import BaseCommand
from matches.models import Match, Fixture, Prediction
from matches.logic.predict import extract_features
import numpy as np

class Command(BaseCommand):
    help = "Diagnose feature extraction and prediction issues"

    def add_arguments(self, parser):
        parser.add_argument('--league', type=int, help='League ID to diagnose')

    def handle(self, *args, **options):
        league_id = options.get('league')
        
        # Check predictions
        self.stdout.write(self.style.NOTICE("\n=== CHECKING PREDICTIONS ==="))
        predictions = Prediction.objects.all()
        if league_id:
            predictions = predictions.filter(fixture__league_id=league_id)
        
        pred_counts = predictions.values('result_pred').annotate(
            count=__import__('django.db.models', fromlist=['Count']).Count('result_pred')
        )
        
        self.stdout.write(f"Total predictions: {predictions.count()}")
        for pred in pred_counts:
            self.stdout.write(f"  {pred['result_pred']}: {pred['count']}")
        
        # Check confidence distribution
        confidences = list(predictions.values_list('confidence', flat=True))
        if confidences:
            self.stdout.write(f"\nConfidence stats:")
            self.stdout.write(f"  Min: {min(confidences):.3f}")
            self.stdout.write(f"  Max: {max(confidences):.3f}")
            self.stdout.write(f"  Mean: {np.mean(confidences):.3f}")
            self.stdout.write(f"  Unique values: {len(set(confidences))}")
        
        # Sample feature extraction
        self.stdout.write(self.style.NOTICE("\n=== SAMPLING FEATURE EXTRACTION ==="))
        
        # Get sample fixtures
        fixtures = Fixture.objects.filter(status__icontains="Not Started")
        if league_id:
            fixtures = fixtures.filter(league_id=league_id)
        
        sample_fixtures = fixtures[:5]
        
        for i, fixture in enumerate(sample_fixtures, 1):
            self.stdout.write(f"\nFixture {i}: {fixture.home_team} vs {fixture.away_team} ({fixture.date.date()})")
            try:
                features = extract_features(fixture, date=fixture.date)
                self.stdout.write("  Features:")
                for key, value in features.items():
                    self.stdout.write(f"    {key}: {value:.4f}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error: {e}"))
        
        # Check past matches for teams
        self.stdout.write(self.style.NOTICE("\n=== CHECKING HISTORICAL DATA ==="))
        if sample_fixtures:
            fixture = sample_fixtures[0]
            query_filter = {}
            if league_id:
                query_filter['league_id'] = league_id
            
            home_matches = Match.objects.filter(
                __import__('django.db.models', fromlist=['Q']).Q(home_team=fixture.home_team) | 
                __import__('django.db.models', fromlist=['Q']).Q(away_team=fixture.home_team),
                home_score__isnull=False,
                away_score__isnull=False,
                **query_filter
            ).order_by('-date')
            
            self.stdout.write(f"{fixture.home_team.name}: {home_matches.count()} historical matches")
            
            away_matches = Match.objects.filter(
                __import__('django.db.models', fromlist=['Q']).Q(home_team=fixture.away_team) | 
                __import__('django.db.models', fromlist=['Q']).Q(away_team=fixture.away_team),
                home_score__isnull=False,
                away_score__isnull=False,
                **query_filter
            ).order_by('-date')
            
            self.stdout.write(f"{fixture.away_team.name}: {away_matches.count()} historical matches")
