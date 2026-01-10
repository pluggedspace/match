from matches.logic.feature_training import (
    calculate_form, 
    calculate_strength, 
    count_injuries,
    calculate_goal_average,
    get_home_away_records
)

def extract_features(obj, date=None):
    """
    Extracts enhanced features from either a Match (historical) or Fixture (upcoming).
    """
    home = getattr(obj, 'home_team', None)
    away = getattr(obj, 'away_team', None)
    
    # Use object's date if not explicitly provided
    if not date and hasattr(obj, 'date'):
        date = obj.date

    if not home or not away:
        raise ValueError("Object must have home_team and away_team attributes.")

    # Calculate home and away specific features
    home_win_rate, home_draw_rate, home_loss_rate = get_home_away_records(home, is_home=True, date=date)
    away_win_rate, away_draw_rate, away_loss_rate = get_home_away_records(away, is_home=False, date=date)

    return {
        # Basic features
        "home_form": calculate_form(home, date=date),
        "away_form": calculate_form(away, date=date),
        "home_strength": calculate_strength(home, date=date),
        "away_strength": calculate_strength(away, date=date),
        "home_injuries": count_injuries(home, date=date),
        "away_injuries": count_injuries(away, date=date),
        
        # Enhanced features
        "home_goal_avg": calculate_goal_average(home, home_only=True, date=date),
        "away_goal_avg": calculate_goal_average(away, away_only=True, date=date),
        "form_diff": calculate_form(home, date=date) - calculate_form(away, date=date),
        "strength_diff": calculate_strength(home, date=date) - calculate_strength(away, date=date),
        
        # Home/away specific records
        "home_win_rate": home_win_rate,
        "home_draw_rate": home_draw_rate,
        "away_win_rate": away_win_rate,
        "away_draw_rate": away_draw_rate,
        
        # Combined features
        "home_advantage": home_win_rate - away_win_rate,
    }