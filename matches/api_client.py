import requests
import datetime


API_KEY = '1ecad14232mshea32a62c1e4dc2ap181062jsn38bf6995676a' 
BASE_URL = 'https://api-football-v1.p.rapidapi.com/v3'

HEADERS = {
    'X-RapidAPI-Key': API_KEY,
    'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'
}

def get_leagues():
    url = f'{BASE_URL}/leagues'
    response = requests.get(url, headers=HEADERS)
    return response.json()

def get_teams(league_id, season):
    url = f'{BASE_URL}/teams'
    params = {'league': league_id, 'season': season}
    response = requests.get(url, headers=HEADERS, params=params)
    return response.json()

def get_league_by_id(league_id):
    """
    Fetch league details (name, country, etc.) from API-Football by league_id.
    """
    url = f"{BASE_URL}/leagues"
    params = {"id": league_id}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['response']:
            return data['response'][0]['league']['name']
        else:
            return None
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")

def get_league_id_by_name(league_name, season):
    """
    Find a league_id from API-Football by its name and season.
    Case-insensitive match.
    """
    url = f"{BASE_URL}/leagues"
    params = {"season": season}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json()
        for item in data['response']:
            if item['league']['name'].lower() == league_name.lower():
                return item['league']['id']
        return None
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")

def get_league_id_by_name_and_country(league_name, country_name, season):
    """
    Find a league_id from API-Football by its name and country for a given season.
    Case-insensitive match for both.
    """
    url = f"{BASE_URL}/leagues"
    params = {"season": season}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json()
        for item in data['response']:
            if (
                item['league']['name'].lower() == league_name.lower() and
                item['country']['name'].lower() == country_name.lower()
            ):
                return item['league']['id']
        return None
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")


def get_fixtures(league_id=None, season=None, next_n=10):
    """
    Fetch the next N fixtures, optionally filtered by league and season.
    """
    url = f"{BASE_URL}/fixtures"
    params = {"next": next_n}

    if league_id:
        params["league"] = league_id
    if season:
        params["season"] = season

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")

        
        
def get_players_by_team(team_id, season=2025):
    url = f"{BASE_URL}/players"
    params = {
        'team': team_id,
        'season': season
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")
        
        
def get_past_fixtures(league_id=39, season=2024, count=380):
    url = f"{BASE_URL}/fixtures"
    params = {
        'league': league_id,
        'season': season,
        'status': 'FT',  # Finished matches
        'last': count
    }

    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")
        
        
