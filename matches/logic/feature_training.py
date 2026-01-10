from matches.models import Match, Player
from django.db.models import Q
from datetime import datetime, date, timedelta 
import logging

logger = logging.getLogger(__name__)

def get_recent_matches(team, limit=20, date=None):
    try:
        # Build query with Q objects for proper combination
        query = Q(home_team=team) | Q(away_team=team)
        # Filter for matches that have results (not scores, since data doesn't have scores)
        query &= Q(result__isnull=False)
        
        # If a date is provided, only look at matches BEFORE this date
        if date:
            query &= Q(date__lt=date)
            
        matches = Match.objects.filter(query).order_by('-date')[:limit]
        logger.debug(f"Found {matches.count()} recent matches for {team.name} (before {date})")
        return matches
    except Exception as e:
        logger.error(f"Error getting recent matches for {team.name if team else 'None'}: {e}")
        return Match.objects.none()

def calculate_strength(team, limit=20, date=None):
    """
    Strength = average goal difference if scores available, otherwise win/draw rate.
    Returns a value between -3 and 3 (for goal diff) or -1 to 1 (for win rate).
    """
    try:
        matches = get_recent_matches(team, limit=limit, date=date)
        if not matches:
            logger.debug(f"No matches found for {team.name}, returning 0 strength")
            return 0.0

        # Check if we have score data
        has_scores = any(m.home_score is not None and m.away_score is not None for m in matches)
        
        if has_scores:
            # Use goal difference (better metric when available)
            scored = conceded = 0
            for m in matches:
                if m.home_score is not None and m.away_score is not None:
                    if m.home_team == team:
                        scored += float(m.home_score)
                        conceded += float(m.away_score)
                    else:
                        scored += float(m.away_score)
                        conceded += float(m.home_score)
            
            strength = (scored - conceded) / len(matches)
            logger.debug(f"Strength for {team.name}: {strength} (from goals)")
            return strength
        else:
            # Fallback to result-based calculation
            wins = draws = losses = 0
            for m in matches:
                if m.home_team == team:
                    result = m.result
                else:
                    # Invert result for away team
                    result = {'win': 'loss', 'loss': 'win', 'draw': 'draw'}.get(m.result, m.result)
                
                if result == 'win':
                    wins += 1
                elif result == 'draw':
                    draws += 1
                else:
                    losses += 1

            # Strength based on points: (wins*3 + draws*1) / max_possible - 0.5
            points = wins * 3 + draws
            max_points = len(matches) * 3
            strength = (points / max_points - 0.5) * 2 if max_points > 0 else 0.0
            
            logger.debug(f"Strength for {team.name}: {strength} (from results)")
            return strength
        
    except Exception as e:
        logger.error(f"Error calculating strength for {team.name}: {e}")
        return 0.0

def calculate_form(team, limit=20, decay=0.9, date=None):
    """
    Form calculation using scores if available, otherwise result field
    """
    try:
        matches = get_recent_matches(team, limit=limit, date=date)
        if not matches:
            logger.debug(f"No matches found for {team.name}, returning 0 form")
            return 0.0

        # Check if we have score data
        has_scores = any(m.home_score is not None and m.away_score is not None for m in matches)
        
        total_points = 0
        for m in matches:
            if has_scores and m.home_score is not None and m.away_score is not None:
                # Calculate from scores
                if m.home_team == team:
                    team_goals = float(m.home_score)
                    opp_goals = float(m.away_score)
                else:
                    team_goals = float(m.away_score)
                    opp_goals = float(m.home_score)
                
                if team_goals > opp_goals:
                    total_points += 3
                elif team_goals == opp_goals:
                    total_points += 1
            else:
                # Fallback to result field
                if m.home_team == team:
                    result = m.result
                else:
                    # Invert result for away team
                    result = {'win': 'loss', 'loss': 'win', 'draw': 'draw'}.get(m.result, m.result)

                if result == 'win':
                    total_points += 3
                elif result == 'draw':
                    total_points += 1

        form = total_points / (len(matches) * 3)  # Normalize to 0-1
        logger.debug(f"Form for {team.name}: {form} ({'from scores' if has_scores else 'from results'})")
        return form
        
    except Exception as e:
        logger.error(f"Error calculating form for {team.name}: {e}")
        return 0.0

def calculate_goal_average(team, home_only=False, away_only=False, limit=10, date=None):
    """
    Calculate average goals scored by team.
    Uses actual scores if available, otherwise estimates from win rate.
    """
    try:
        matches = get_recent_matches(team, limit=limit, date=date)
        if not matches:
            return 1.5  # League average estimate
        
        # Check if we have score data
        has_scores = any(m.home_score is not None and m.away_score is not None for m in matches)
        
        if has_scores:
            # Use actual goal data
            total_goals = 0
            count = 0
            
            for m in matches:
                if m.home_score is None or m.away_score is None:
                    continue
                    
                if home_only and m.home_team != team:
                    continue
                if away_only and m.away_team != team:
                    continue
                
                if m.home_team == team:
                    total_goals += float(m.home_score)
                else:
                    total_goals += float(m.away_score)
                count += 1
            
            avg = total_goals / count if count > 0 else 1.5
            logger.debug(f"Goal average for {team.name}: {avg} (from scores)")
            return avg
        else:
            # Estimate from win rate
            wins = 0
            count = 0
            
            for m in matches:
                if home_only and m.home_team != team:
                    continue
                if away_only and m.away_team != team:
                    continue
                
                if m.home_team == team:
                    result = m.result
                else:
                    result = {'win': 'loss', 'loss': 'win', 'draw': 'draw'}.get(m.result, m.result)
                
                if result == 'win':
                    wins += 1
                count += 1
            
            # Estimate goals based on win rate: winners score ~2 goals, others ~1
            win_rate = wins / count if count > 0 else 0.5
            avg = 1.0 + win_rate  # Range from 1.0 to 2.0
            
            logger.debug(f"Goal average for {team.name}: {avg} (estimated from results)")
            return avg
        
    except Exception as e:
        logger.error(f"Error calculating goal average for {team.name}: {e}")
        return 1.5

def get_home_away_records(team, is_home=True, limit=10, date=None):
    """Get win/draw/loss record for home or away matches"""
    try:
        # Build query with Q objects
        if is_home:
            query = Q(home_team=team)
        else:
            query = Q(away_team=team)
        
        query &= Q(result__isnull=False)
        
        if date:
            query &= Q(date__lt=date)

        matches = Match.objects.filter(query).order_by('-date')[:limit]
        
        if not matches:
            return 0.0, 0.0, 0.0
        
        wins = draws = losses = 0
        
        for m in matches:
            if is_home:
                result = m.result
            else:
                # Invert for away team
                result = {'win': 'loss', 'loss': 'win', 'draw': 'draw'}.get(m.result, m.result)
            
            if result == 'win':
                wins += 1
            elif result == 'draw':
                draws += 1
            else:
                losses += 1
        
        total = wins + draws + losses
        win_rate = wins / total if total > 0 else 0.0
        draw_rate = draws / total if total > 0 else 0.0
        loss_rate = losses / total if total > 0 else 0.0
        
        logger.debug(f"Home/away record for {team.name}: wins={win_rate}, draws={draw_rate}, losses={loss_rate}")
        return win_rate, draw_rate, loss_rate
        
    except Exception as e:
        logger.error(f"Error getting home/away record for {team.name}: {e}")
        return 0.0, 0.0, 0.0

def count_injuries(team, season=None, date=None):
    """
    Simple injury counting with smart fallbacks
    """
    try:
        # Use current season from latest match if not specified
        if not season:
            query = Q(home_team=team) | Q(away_team=team)
            if date:
                query &= Q(date__lt=date)
                
            latest_match = Match.objects.filter(
                query
            ).exclude(season__isnull=True).order_by('-date').first()
            
            if latest_match:
                season = latest_match.season
            else:
                # Fallback: use current year season format
                current_year = datetime.now().year
                season = f"{current_year}-{current_year + 1}"
        
        # Get players for this team and season
        players = Player.objects.filter(team=team, season=season)
        total_players = players.count()
        
        if total_players == 0:
            # No player data - use league average estimate
            return 0.1  # 10% average injury rate
        
        # Count confirmed injuries
        confirmed_injured = players.filter(injured=True).count()
        
        # Count players with unknown status
        unknown_status = players.filter(injured__isnull=True).count()
        
        if unknown_status == total_players:
            # All unknown - use estimate
            return 0.1
            
        # Calculate based on known data
        injury_rate = confirmed_injured / (total_players - unknown_status)
        
        # If many unknowns, adjust slightly upward
        if unknown_status > total_players * 0.3:  # If >30% unknown
            injury_rate = min(injury_rate + 0.05, 0.3)  # Add 5% buffer
            
        return injury_rate
        
    except Exception as e:
        logger.error(f"Error counting injuries for {team.name}: {e}")
        return 0.1  # Safe default