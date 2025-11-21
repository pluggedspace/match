from matches.logic.feature_training import (
    calculate_form, 
    calculate_strength, 
    count_injuries,
    calculate_goal_average,
    get_home_away_records
)

def extract_features(obj):
    """
    Extracts enhanced features from either a Match (historical) or Fixture (upcoming).
    """
    home = getattr(obj, 'home_team', None)
    away = getattr(obj, 'away_team', None)

    if not home or not away:
        raise ValueError("Object must have home_team and away_team attributes.")

    # Calculate home and away specific features
    home_win_rate, home_draw_rate, home_loss_rate = get_home_away_records(home, is_home=True)
    away_win_rate, away_draw_rate, away_loss_rate = get_home_away_records(away, is_home=False)

    return {
        # Basic features
        "home_form": calculate_form(home),
        "away_form": calculate_form(away),
        "home_strength": calculate_strength(home),
        "away_strength": calculate_strength(away),
        "home_injuries": count_injuries(home),
        "away_injuries": count_injuries(away),
        
        # Enhanced features
        "home_goal_avg": calculate_goal_average(home, home_only=True),
        "away_goal_avg": calculate_goal_average(away, away_only=True),
        "form_diff": calculate_form(home) - calculate_form(away),
        "strength_diff": calculate_strength(home) - calculate_strength(away),
        
        # Home/away specific records
        "home_win_rate": home_win_rate,
        "home_draw_rate": home_draw_rate,
        "away_win_rate": away_win_rate,
        "away_draw_rate": away_draw_rate,
        
        # Combined features
        "home_advantage": home_win_rate - away_win_rate,
    }