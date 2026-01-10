from matches.models import Match, Prediction, Fixture, ModelConfig
from matches.logic.predict import extract_features
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score
from sklearn.utils import class_weight
import numpy as np
import pandas as pd
from django.db.models import Q
from datetime import datetime, date, timedelta

label_map = {0: 'win', 1: 'draw', 2: 'loss'}
reverse_map = {'win': 0, 'draw': 1, 'loss': 2}

def train_and_predict(league_id=None, competition_id=None, country_id=None):
    context_str = "Global"
    if league_id: context_str = f"League {league_id}"
    elif competition_id: context_str = f"Competition {competition_id}"
    elif country_id: context_str = f"Country {country_id}"

    print(f"Starting training and prediction ({context_str})...")

    # 1. Fetch Model Configuration
    config = None
    if league_id:
        config = ModelConfig.objects.filter(league_id=league_id, active=True).first()
    elif competition_id:
        config = ModelConfig.objects.filter(competition_id=competition_id, active=True).first()
    elif country_id:
        config = ModelConfig.objects.filter(country_id=country_id, active=True).first()
    
    # Fallback to global config if no specific config found (optional, or just use defaults)
    # For now, we'll use defaults if no config found.
    
    hyperparameters = {}
    feature_weights = {}
    
    if config:
        print(f"⚙️  Loaded ModelConfig: {config}")
        
        # detailed mapping from model fields to dicts
        hyperparameters = {
            'n_estimators': config.n_estimators,
            'max_depth': config.max_depth,
            'min_samples_split': config.min_samples_split,
        }
        
        feature_weights = {
            'home_form': config.weight_home_form,
            'away_form': config.weight_away_form,
            'home_strength': config.weight_home_strength,
            'away_strength': config.weight_away_strength,
            'home_injuries': config.weight_home_injuries,
            'away_injuries': config.weight_away_injuries,
            'home_goal_avg': config.weight_home_goal_avg,
            'away_goal_avg': config.weight_away_goal_avg,
            'form_diff': config.weight_form_diff,
            'strength_diff': config.weight_strength_diff,
            'home_win_rate': config.weight_home_win_rate,
            'home_draw_rate': config.weight_home_draw_rate,
            'away_win_rate': config.weight_away_win_rate,
            'away_draw_rate': config.weight_away_draw_rate,
            'home_advantage': config.weight_home_advantage,
        }

        print(f"   Hyperparameters: {hyperparameters}")
        print(f"   Feature Weights: {feature_weights}")

    # 2. Filter Past Matches
    past_matches = Match.objects.exclude(result__isnull=True)
    
    if league_id:
        past_matches = past_matches.filter(league_id=league_id)
    elif competition_id:
        past_matches = past_matches.filter(competition_id=competition_id)
    elif country_id:
        # Matches where at least one team is from the country
        past_matches = past_matches.filter(
            Q(home_team__country_link_id=country_id) | Q(away_team__country_link_id=country_id)
        )

    print(f"📊 Total past matches available for {context_str}: {past_matches.count()}")
    
    if past_matches.count() < 20:
        print(f"⚠️  Insufficient data ({past_matches.count()} samples). Need at least 20 matches.")
        return {"status": "fail", "reason": "Insufficient training data"}

    X, y = [], []

    for match in past_matches:
        try:
            features = extract_features(match, date=match.date)
            
            # Apply feature weights
            row = [
                features['home_form'] * feature_weights.get('home_form', 1.0),
                features['away_form'] * feature_weights.get('away_form', 1.0),
                features['home_strength'] * feature_weights.get('home_strength', 1.0),
                features['away_strength'] * feature_weights.get('away_strength', 1.0),
                features['home_injuries'] * feature_weights.get('home_injuries', 1.0),
                features['away_injuries'] * feature_weights.get('away_injuries', 1.0),
                features['home_goal_avg'] * feature_weights.get('home_goal_avg', 1.0),
                features['away_goal_avg'] * feature_weights.get('away_goal_avg', 1.0),
                features['form_diff'] * feature_weights.get('form_diff', 1.0),
                features['strength_diff'] * feature_weights.get('strength_diff', 1.0),
                features['home_win_rate'] * feature_weights.get('home_win_rate', 1.0),
                features['home_draw_rate'] * feature_weights.get('home_draw_rate', 1.0),
                features['away_win_rate'] * feature_weights.get('away_win_rate', 1.0),
                features['away_draw_rate'] * feature_weights.get('away_draw_rate', 1.0),
                features['home_advantage'] * feature_weights.get('home_advantage', 1.0)
            ]
            
            X.append(row)
            y.append(reverse_map[match.result])
        except Exception as e:
            # print(f"⚠️  Error processing match {match.id}: {e}")
            continue

    if not X:
        print("❌ No training data available after processing")
        return {"status": "fail", "reason": "No valid training data"}

    # Convert to numpy arrays
    X_arr = np.array(X)
    y_arr = np.array(y)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=0.2, random_state=42, stratify=y_arr
    )

    # Calculate class weights for imbalance
    class_weights = class_weight.compute_class_weight(
        'balanced', classes=np.unique(y_train), y=y_train
    )
    class_weight_dict = dict(zip(np.unique(y_train), class_weights))

    # Initialize model with hyperparameters
    n_estimators = int(hyperparameters.get('n_estimators', 100))
    max_depth = hyperparameters.get('max_depth', 10)
    if max_depth is not None: max_depth = int(max_depth)
    min_samples_split = int(hyperparameters.get('min_samples_split', 5))

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        random_state=42,
        class_weight=class_weight_dict
    )

    # Cross-validation check
    cv_scores = cross_val_score(model, X_arr, y_arr, cv=min(5, len(X_arr)))
    print(f"Mean CV accuracy: {cv_scores.mean():.3f}")

    # Train the model
    model.fit(X_train, y_train)
    
    # Test accuracy
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"✅ Training complete. Test accuracy: {accuracy:.4f}")

    # PREDICT FOR UPCOMING FIXTURES
    upcoming_fixtures = Fixture.objects.filter(status__icontains="Not Started")
    
    if league_id:
        upcoming_fixtures = upcoming_fixtures.filter(league_id=league_id)
    elif competition_id:
        upcoming_fixtures = upcoming_fixtures.filter(competition_id=competition_id)
    elif country_id:
        upcoming_fixtures = upcoming_fixtures.filter(
            Q(home_team__country_link_id=country_id) | Q(away_team__country_link_id=country_id)
        )

    matches_predicted = 0
    print(f"🎯 Predicting for {upcoming_fixtures.count()} upcoming fixtures ({context_str})...")

    for fixture in upcoming_fixtures:
        try:
            features = extract_features(fixture, date=fixture.date)
            X_fixture = [[
                features['home_form'] * feature_weights.get('home_form', 1.0),
                features['away_form'] * feature_weights.get('away_form', 1.0),
                features['home_strength'] * feature_weights.get('home_strength', 1.0),
                features['away_strength'] * feature_weights.get('away_strength', 1.0),
                features['home_injuries'] * feature_weights.get('home_injuries', 1.0),
                features['away_injuries'] * feature_weights.get('away_injuries', 1.0),
                features['home_goal_avg'] * feature_weights.get('home_goal_avg', 1.0),
                features['away_goal_avg'] * feature_weights.get('away_goal_avg', 1.0),
                features['form_diff'] * feature_weights.get('form_diff', 1.0),
                features['strength_diff'] * feature_weights.get('strength_diff', 1.0),
                features['home_win_rate'] * feature_weights.get('home_win_rate', 1.0),
                features['home_draw_rate'] * feature_weights.get('home_draw_rate', 1.0),
                features['away_win_rate'] * feature_weights.get('away_win_rate', 1.0),
                features['away_draw_rate'] * feature_weights.get('away_draw_rate', 1.0),
                features['home_advantage'] * feature_weights.get('home_advantage', 1.0)
            ]]

            pred = model.predict(X_fixture)[0]
            probs = model.predict_proba(X_fixture)[0]

            # Apply smoothing
            smoothing = 0.01
            probs = probs + smoothing
            probs = probs / probs.sum()

            # Slight draw boost
            draw_boost = 0.03
            probs[1] = min(probs[1] + draw_boost, 0.95)
            probs = probs / probs.sum()

            # Get confidence and predicted result
            confidence = float(max(probs))
            predicted_result = label_map[pred]
            
            model_version = "v1"
            if league_id: model_version = f"v1-L{league_id}"
            elif competition_id: model_version = f"v1-C{competition_id}"
            elif country_id: model_version = f"v1-CT{country_id}"

            # Save prediction
            Prediction.objects.update_or_create(
                fixture=fixture,
                defaults={
                    'result_pred': predicted_result,
                    'confidence': confidence,
                    'goal_diff': features['home_strength'] - features['away_strength'],
                    'fair_odds_home': round(1 / probs[0], 2),
                    'fair_odds_draw': round(1 / probs[1], 2),
                    'fair_odds_away': round(1 / probs[2], 2),
                    'model_version': model_version
                }
            )
            matches_predicted += 1

        except Exception as e:
            # print(f"⚠️  Error predicting fixture {fixture.id}: {e}")
            continue

    print(f"🏁 Prediction completed. Matches predicted: {matches_predicted}")

    return {
        "status": "success",
        "accuracy": round(accuracy, 4),
        "matches_predicted": matches_predicted,
        "cv_score": round(cv_scores.mean(), 3)
    }