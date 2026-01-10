import os
import joblib
import numpy as np
from django.core.management.base import BaseCommand
from matches.models import Match, Prediction, Fixture, ModelConfig
from matches.logic.predict import extract_features
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score
from sklearn.utils import class_weight

MODEL_PATH = os.path.join('matches', 'models', 'ml_model.pkl')

class Command(BaseCommand):
    help = 'Train or load model and predict upcoming matches'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model-version',
            type=str,
            default='v2',
            help='Model version to tag predictions with'
        )
        parser.add_argument(
            '--retrain',
            action='store_true',
            help='Force retrain even if model exists'
        )
        parser.add_argument('--league', type=int, help='League ID to train for')
        parser.add_argument('--competition', type=int, help='Competition ID to train for')
        parser.add_argument('--country', type=int, help='Country ID to train for')

    def handle(self, *args, **kwargs):
        from matches.logic.train_and_predict import train_and_predict
        
        league_id = kwargs.get('league')
        competition_id = kwargs.get('competition')
        country_id = kwargs.get('country')
        
        self.stdout.write(self.style.NOTICE(f"🚀 Starting training process..."))
        if league_id: self.stdout.write(f"   Scope: League {league_id}")
        if competition_id: self.stdout.write(f"   Scope: Competition {competition_id}")
        if country_id: self.stdout.write(f"   Scope: Country {country_id}")

        try:
            result = train_and_predict(
                league_id=league_id, 
                competition_id=competition_id, 
                country_id=country_id
            )
            
            if result.get("status") == "success":
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Success!\n"
                    f"   Matches Predicted: {result['matches_predicted']}\n"
                    f"   Accuracy: {result['accuracy']}\n"
                    f"   CV Score: {result.get('cv_score', 'N/A')}"
                ))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Failed: {result.get('reason')}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"💥 Error: {e}"))