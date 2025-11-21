# utils/api_import.py
import requests
from django.conf import settings
from matches.models import Player, Team

def import_players_from_api(team_external_id, season):
    """
    Example using API-Football to get player data
    """
    try:
        url = "https://api-football-v1.p.rapidapi.com/v3/players"
        querystring = {"team": team_external_id, "season": season}
        headers = {
            "X-RapidAPI-Key": settings.FOOTBALL_API_KEY,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            return response.json()['response']
        return None
        
    except Exception as e:
        print(f"API import error: {e}")
        return None