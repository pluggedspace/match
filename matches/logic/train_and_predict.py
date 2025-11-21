from matches.models import Match, Prediction, Fixture
from matches.logic.predict import extract_features
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score
from sklearn.utils import class_weight
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta  # import what you need

label_map = {0: 'win', 1: 'draw', 2: 'loss'}
reverse_map = {'win': 0, 'draw': 1, 'loss': 2}

def train_and_predict():
    print("Starting training and prediction with enhanced features...")
    
    # TRAIN FROM PAST MATCHES
    past_matches = Match.objects.exclude(result__isnull=True)
    X, y = [], []

    print(f"📊 Total past matches available: {past_matches.count()}")

    for match in past_matches:
        try:
            features = extract_features(match)
            X.append([
                features['home_form'],
                features['away_form'],
                features['home_strength'],
                features['away_strength'],
                features['home_injuries'],
                features['away_injuries'],
                features['home_goal_avg'],
                features['away_goal_avg'],
                features['form_diff'],
                features['strength_diff'],
                features['home_win_rate'],
                features['home_draw_rate'],
                features['away_win_rate'],
                features['away_draw_rate'],
                features['home_advantage']
            ])
            y.append(reverse_map[match.result])
        except Exception as e:
            print(f"⚠️  Error processing match {match.id}: {e}")
            continue

    if not X:
        print("❌ No training data available")
        return {"status": "fail", "reason": "No historical data"}

    # Convert to numpy arrays
    X_arr = np.array(X)
    y_arr = np.array(y)

    # DEBUG: Feature statistics
    print("\n📈 Feature statistics:")
    feature_names = [
        'home_form', 'away_form', 'home_strength', 'away_strength', 
        'home_injuries', 'away_injuries', 'home_goal_avg', 'away_goal_avg',
        'form_diff', 'strength_diff', 'home_win_rate', 'home_draw_rate',
        'away_win_rate', 'away_draw_rate', 'home_advantage'
    ]
    
    for i, feature_name in enumerate(feature_names):
        print(f"{feature_name}: mean={X_arr[:, i].mean():.3f}, std={X_arr[:, i].std():.3f}")

    # DEBUG: Class distribution
    unique, counts = np.unique(y_arr, return_counts=True)
    print(f"\n🎯 Class distribution:")
    for cls, count in zip(unique, counts):
        print(f"{label_map[cls]}: {count} matches ({(count/len(y_arr)*100):.1f}%)")

    # Check if we have enough data for training
    if len(X_arr) < 20:
        print(f"⚠️  Insufficient data ({len(X_arr)} samples). Need at least 20 matches.")
        return {"status": "fail", "reason": "Insufficient training data"}

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=0.2, random_state=42, stratify=y_arr
    )

    # Calculate class weights for imbalance
    class_weights = class_weight.compute_class_weight(
        'balanced', classes=np.unique(y_train), y=y_train
    )
    class_weight_dict = dict(zip(np.unique(y_train), class_weights))

    # Initialize model with class weights
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight=class_weight_dict,
        max_depth=10,
        min_samples_split=5
    )

    # Cross-validation check
    print("\n🔍 Cross-validation check:")
    cv_scores = cross_val_score(model, X_arr, y_arr, cv=min(5, len(X_arr)))
    print(f"CV scores: {[f'{score:.3f}' for score in cv_scores]}")
    print(f"Mean CV accuracy: {cv_scores.mean():.3f}")

    # Train the model
    model.fit(X_train, y_train)
    
    # Test accuracy
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n✅ Training complete. Test accuracy: {accuracy:.4f}")

    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n📊 Feature importance:")
    print(feature_importance.head(10))

    # PREDICT FOR UPCOMING FIXTURES
    upcoming_fixtures = Fixture.objects.filter(status__icontains="Not Started")
    matches_predicted = 0

    print(f"\n🎯 Predicting for {upcoming_fixtures.count()} upcoming fixtures...")

    for fixture in upcoming_fixtures:
        try:
            features = extract_features(fixture)
            X_fixture = [[
                features['home_form'],
                features['away_form'],
                features['home_strength'],
                features['away_strength'],
                features['home_injuries'],
                features['away_injuries'],
                features['home_goal_avg'],
                features['away_goal_avg'],
                features['form_diff'],
                features['strength_diff'],
                features['home_win_rate'],
                features['home_draw_rate'],
                features['away_win_rate'],
                features['away_draw_rate'],
                features['home_advantage']
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
                }
            )
            matches_predicted += 1

            # Debug output for first few predictions
            if matches_predicted <= 3:
                print(f"   {fixture.home_team} vs {fixture.away_team}: {predicted_result} ({confidence:.2f})")

        except Exception as e:
            print(f"⚠️  Error predicting fixture {fixture.id}: {e}")
            continue

    print(f"\n🏁 Prediction completed. Matches predicted: {matches_predicted}")

    return {
        "status": "success",
        "accuracy": round(accuracy, 4),
        "matches_predicted": matches_predicted,
        "cv_score": round(cv_scores.mean(), 3)
    }