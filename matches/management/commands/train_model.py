import os
import joblib
import numpy as np
from django.core.management.base import BaseCommand
from matches.models import Match, Prediction, Fixture
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
            default='v2',  # Updated version
            help='Model version to tag predictions with'
        )
        parser.add_argument(
            '--retrain',
            action='store_true',
            help='Force retrain even if model exists'
        )

    def handle(self, *args, **kwargs):
        model_version = kwargs.get('model_version', 'v2')
        retrain = kwargs.get('retrain', False)
        model = None

        if os.path.exists(MODEL_PATH) and not retrain:
            self.stdout.write(self.style.NOTICE("📦 Loading saved model..."))
            try:
                model = joblib.load(MODEL_PATH)
                self.stdout.write(self.style.SUCCESS("✅ Model loaded successfully"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Failed to load model: {e}. Training new one..."))
                model = self.train_and_save_model()
        else:
            self.stdout.write(self.style.NOTICE("🔨 Training new model..."))
            model = self.train_and_save_model()

        if model:
            self.predict_upcoming(model, model_version)
        else:
            self.stdout.write(self.style.ERROR("❌ Model unavailable. Aborting."))

    def train_and_save_model(self):
        past_matches = Match.objects.exclude(result__isnull=True)
        X, y = [], []

        self.stdout.write(self.style.NOTICE(f"📊 Processing {past_matches.count()} past matches..."))

        for match in past_matches:
            try:
                f = extract_features(match)
                X.append([
                    f["home_form"],
                    f["away_form"],
                    f["home_strength"],
                    f["away_strength"],
                    f["home_injuries"],
                    f["away_injuries"],
                    f["home_goal_avg"],
                    f["away_goal_avg"],
                    f["form_diff"],
                    f["strength_diff"],
                    f["home_win_rate"],
                    f["home_draw_rate"],
                    f["away_win_rate"],
                    f["away_draw_rate"],
                    f["home_advantage"]
                ])
                y.append({'win': 0, 'draw': 1, 'loss': 2}[match.result])
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Skipping match {match.id}: {e}"))
                continue

        if not X:
            self.stdout.write(self.style.WARNING("⚠️ No valid data to train."))
            return None

        X_arr = np.array(X)
        y_arr = np.array(y)

        # Debug output
        self.stdout.write(self.style.NOTICE(f"📈 Training on {len(X_arr)} samples"))
        
        # Check class distribution
        unique, counts = np.unique(y_arr, return_counts=True)
        for cls, count in zip(unique, counts):
            cls_name = {0: 'win', 1: 'draw', 2: 'loss'}[cls]
            self.stdout.write(self.style.NOTICE(f"   {cls_name}: {count} samples ({(count/len(y_arr)*100):.1f}%)"))

        X_train, X_test, y_train, y_test = train_test_split(
            X_arr, y_arr, test_size=0.2, random_state=42, stratify=y_arr
        )

        # Handle class imbalance
        class_weights = class_weight.compute_class_weight(
            'balanced', classes=np.unique(y_train), y=y_train
        )
        class_weight_dict = dict(zip(np.unique(y_train), class_weights))

        model = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight=class_weight_dict,
            max_depth=10,
            min_samples_split=5
        )

        # Cross-validation check
        cv_scores = cross_val_score(model, X_arr, y_arr, cv=min(5, len(X_arr)))
        self.stdout.write(self.style.NOTICE(f"🔍 Cross-validation: {[f'{s:.3f}' for s in cv_scores]}"))
        self.stdout.write(self.style.NOTICE(f"📊 Mean CV accuracy: {cv_scores.mean():.3f}"))

        model.fit(X_train, y_train)

        acc = accuracy_score(y_test, model.predict(X_test))
        self.stdout.write(self.style.SUCCESS(f"🎯 Model trained. Test accuracy: {acc:.2%}"))

        # Save model
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        self.stdout.write(self.style.SUCCESS(f"💾 Model saved to {MODEL_PATH}"))

        return model

    def predict_upcoming(self, model, model_version):
        label_map = {0: 'win', 1: 'draw', 2: 'loss'}
        # Use Fixture instead of Match for upcoming games
        upcoming = Fixture.objects.filter(status__icontains="Not Started")

        self.stdout.write(self.style.NOTICE(f"🔍 Predicting {upcoming.count()} upcoming matches..."))

        predictions_made = 0
        for fixture in upcoming:
            try:
                f = extract_features(fixture)
                X_pred = [[
                    f["home_form"],
                    f["away_form"],
                    f["home_strength"],
                    f["away_strength"],
                    f["home_injuries"],
                    f["away_injuries"],
                    f["home_goal_avg"],
                    f["away_goal_avg"],
                    f["form_diff"],
                    f["strength_diff"],
                    f["home_win_rate"],
                    f["home_draw_rate"],
                    f["away_win_rate"],
                    f["away_draw_rate"],
                    f["home_advantage"]
                ]]

                pred = model.predict(X_pred)[0]
                probs = model.predict_proba(X_pred)[0]

                # Apply smoothing and normalization
                smoothing = 0.01
                probs = probs + smoothing
                probs = probs / probs.sum()

                # Slight draw boost
                draw_boost = 0.03
                probs[1] = min(probs[1] + draw_boost, 0.95)
                probs = probs / probs.sum()

                Prediction.objects.update_or_create(
                    fixture=fixture,  # Changed from match to fixture
                    defaults={
                        'result_pred': label_map[pred],
                        'confidence': float(max(probs)),
                        'goal_diff': int(round(f["home_strength"] - f["away_strength"])),
                        'fair_odds_home': round(1 / probs[0], 2),
                        'fair_odds_draw': round(1 / probs[1], 2),
                        'fair_odds_away': round(1 / probs[2], 2),
                        'model_version': model_version,
                    }
                )
                predictions_made += 1

                if predictions_made <= 3:  # Show first 3 predictions for debugging
                    self.stdout.write(self.style.NOTICE(
                        f"   {fixture.home_team} vs {fixture.away_team}: "
                        f"{label_map[pred]} (conf: {max(probs):.2f})"
                    ))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Fixture {fixture.id} failed prediction: {e}"))

        self.stdout.write(self.style.SUCCESS(f"🏁 Prediction completed. {predictions_made} predictions made."))