from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from matches.models import Team, Match, League, Season
from matches.logic.feature_training import calculate_form

class FeatureExtractionTest(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Test Team")
        self.opponent = Team.objects.create(name="Opponent")
        self.league = League.objects.create(name="Test League")
        
        # Create matches over time
        # Match 1: Win (3 points) - 30 days ago
        Match.objects.create(
            home_team=self.team,
            away_team=self.opponent,
            home_score=2,
            away_score=0,
            date=timezone.now() - timedelta(days=30),
            league=self.league,
            season="2024",
            fixture_id="m1"
        )
        
        # Match 2: Loss (0 points) - 20 days ago
        Match.objects.create(
            home_team=self.team,
            away_team=self.opponent,
            home_score=0,
            away_score=2,
            date=timezone.now() - timedelta(days=20),
            league=self.league,
            season="2024",
            fixture_id="m2"
        )
        
        # Match 3: Win (3 points) - 10 days ago
        Match.objects.create(
            home_team=self.team,
            away_team=self.opponent,
            home_score=1,
            away_score=0,
            date=timezone.now() - timedelta(days=10),
            league=self.league,
            season="2024",
            fixture_id="m3"
        )

    def test_form_calculation_at_different_dates(self):
        # Date 1: After Match 1, Before Match 2
        date1 = timezone.now() - timedelta(days=25)
        form1 = calculate_form(self.team, date=date1)
        # Should only see Match 1 (Win) -> 3 points / 3 max = 1.0
        self.assertEqual(form1, 1.0, "Form should be 1.0 after first win")

        # Date 2: After Match 2, Before Match 3
        date2 = timezone.now() - timedelta(days=15)
        form2 = calculate_form(self.team, date=date2)
        # Should see Match 1 (Win) and Match 2 (Loss) -> 3 points / 6 max = 0.5
        self.assertEqual(form2, 0.5, "Form should be 0.5 after win and loss")

        # Date 3: After Match 3
        date3 = timezone.now()
        form3 = calculate_form(self.team, date=date3)
        # Should see Match 1, 2, 3 -> 6 points / 9 max = 0.66...
        self.assertAlmostEqual(form3, 0.6666, places=4, msg="Form should be 0.66 after win, loss, win")
        
    def test_future_data_leakage(self):
        # Check form at a date BEFORE any matches
        date_early = timezone.now() - timedelta(days=40)
        form_early = calculate_form(self.team, date=date_early)
        self.assertEqual(form_early, 0.0, "Form should be 0.0 before any matches")
