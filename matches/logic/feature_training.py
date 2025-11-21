from matches.models import Match, Player
from django.db.models import Q
from datetime import datetime, date, timedelta 
import logging

logger = logging.getLogger(__name__)

def get_recent_matches(team, limit=20):
    try:
        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            home_score__isnull=False,
            away_score__isnull=False
        ).order_by('-date')[:limit]
        logger.debug(f"Found {matches.count()} recent matches for {team.name}")
        return matches
    except Exception as e:
        logger.error(f"Error getting recent matches for {team.name if team else 'None'}: {e}")
        return Match.objects.none()

def calculate_strength(team, limit=20):
    """
    Strength = average goal difference over recent matches.
    """
    try:
        matches = get_recent_matches(team, limit=limit)
        if not matches:
            logger.debug(f"No matches found for {team.name}, returning 0 strength")
            return 0.0

        scored = conceded = 0
        for m in matches:
            if m.home_team == team:
                scored += float(m.home_score or 0)
                conceded += float(m.away_score or 0)
            else:
                scored += float(m.away_score or 0)
                conceded += float(m.home_score or 0)

        strength = (scored - conceded) / len(matches)
        logger.debug(f"Strength for {team.name}: {strength}")
        return strength
        
    except Exception as e:
        logger.error(f"Error calculating strength for {team.name}: {e}")
        return 0.0

def calculate_form(team, limit=20, decay=0.9):
    """
    Simple form calculation without circular dependencies
    """
    try:
        matches = get_recent_matches(team, limit=limit)
        if not matches:
            logger.debug(f"No matches found for {team.name}, returning 0 form")
            return 0.0

        total_points = 0
        for m in matches:
            if m.home_team == team:
                team_goals = float(m.home_score or 0)
                opp_goals = float(m.away_score or 0)
            else:
                team_goals = float(m.away_score or 0)
                opp_goals = float(m.home_score or 0)

            if team_goals > opp_goals:
                total_points += 3
            elif team_goals == opp_goals:
                total_points += 1

        form = total_points / (len(matches) * 3)  # Normalize to 0-1
        logger.debug(f"Form for {team.name}: {form}")
        return form
        
    except Exception as e:
        logger.error(f"Error calculating form for {team.name}: {e}")
        return 0.0

def calculate_goal_average(team, home_only=False, away_only=False, limit=10):
    """Calculate average goals scored by team"""
    try:
        matches = get_recent_matches(team, limit=limit)
        if not matches:
            return 0.0
        
        total_goals = 0
        count = 0
        
        for m in matches:
            if home_only and m.home_team != team:
                continue
            if away_only and m.away_team != team:
                continue
                
            if m.home_team == team:
                total_goals += float(m.home_score or 0)
            else:
                total_goals += float(m.away_score or 0)
            count += 1
        
        avg = total_goals / count if count > 0 else 0.0
        logger.debug(f"Goal average for {team.name}: {avg}")
        return avg
        
    except Exception as e:
        logger.error(f"Error calculating goal average for {team.name}: {e}")
        return 0.0

def get_home_away_records(team, is_home=True, limit=10):
    """Get win/draw/loss record for home or away matches"""
    try:
        if is_home:
            matches = Match.objects.filter(
                home_team=team, 
                home_score__isnull=False,
                away_score__isnull=False
            ).order_by('-date')[:limit]
        else:
            matches = Match.objects.filter(
                away_team=team, 
                home_score__isnull=False,
                away_score__isnull=False
            ).order_by('-date')[:limit]
        
        if not matches:
            return 0.0, 0.0, 0.0
        
        wins = draws = losses = 0
        
        for m in matches:
            if is_home:
                if float(m.home_score or 0) > float(m.away_score or 0):
                    wins += 1
                elif float(m.home_score or 0) == float(m.away_score or 0):
                    draws += 1
                else:
                    losses += 1
            else:
                if float(m.away_score or 0) > float(m.home_score or 0):
                    wins += 1
                elif float(m.away_score or 0) == float(m.home_score or 0):
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

def count_injuries(team, season=None):
    """
    Simple injury counting with smart fallbacks
    """
    try:
        # Use current season from latest match if not specified
        if not season:
            latest_match = Match.objects.filter(
                Q(home_team=team) | Q(away_team=team)
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