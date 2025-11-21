# matches/models
import csv
import json
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime

RESULT_MAP = {
    "H": "win",
    "A": "loss",
    "D": "draw",
    "win": "win",
    "loss": "loss",
    "draw": "draw",
}

# ------------------------------
# Teams (canonical, no duplicates)
# ------------------------------
class Team(models.Model):
    api_id = models.CharField(max_length=50, null=True, blank=True, unique=False)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50, default="England")

    class Meta:
        unique_together = ("name", "country")

    def __str__(self):
        return f"{self.name} ({self.country})"

    @classmethod
    def get_or_create_canonical(cls, name, country="England", api_id=None):
        if api_id:
            team, _ = cls.objects.get_or_create(api_id=api_id, defaults={"name": name, "country": country})
        else:
            team, _ = cls.objects.get_or_create(name=name, country=country)
        return team

    @classmethod
    def import_from_csv(cls, file_path, league=None):
        # league parameter is kept for consistency but not used in Team import
        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                cls.get_or_create_canonical(row["name"], api_id=row.get("api_id"))

    @classmethod
    def import_from_json(cls, file_path, league=None):
        # league parameter is kept for consistency but not used in Team import
        with open(file_path, encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)
            for item in data:
                cls.get_or_create_canonical(item["name"], api_id=item.get("api_id"))


# ------------------------------
# League
# ------------------------------
class League(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, null=True)  # e.g. "EPL", "LALIGA"
    country = models.CharField(max_length=50, blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @classmethod
    def get_or_create_league(cls, name, code=None, country=None):
        """Helper to always get or create a League instance safely."""
        if not code:
            code = name[:6].upper().replace(" ", "")
        league, _ = cls.objects.get_or_create(
            name=name,
            defaults={
                "code": code,
                "country": country or "",
            },
        )
        return league


# ------------------------------
# Fixtures
# ------------------------------
class Fixture(models.Model):
    id = models.IntegerField(primary_key=True)
    date = models.DateTimeField()
    status = models.CharField(max_length=50)
    league = models.ForeignKey('League', on_delete=models.CASCADE, related_name='fixtures', db_column='league', null=True, blank=True)
    season = models.CharField(max_length=20)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_fixtures")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_fixtures")

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.season})"

    @staticmethod
    def canonical_fixture_id(home_team, away_team, league, season, date):
        return f"{league.code}-{season}-{home_team.id}-{away_team.id}-{date.date()}"

    @classmethod
    def import_from_csv(cls, file_path, league=None, season=None):
        # If league is a string, convert it to League instance for backward compatibility
        if isinstance(league, str):
            league = League.get_or_create_league(league)
        elif league is None:
            league = League.get_or_create_league("Premier League")
        
        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            imported = 0
            for row in reader:
                try:
                    home_team = Team.get_or_create_canonical(
                        name=row.get("home_team_name") or row.get("HomeTeam"),
                        api_id=row.get("home_team_api_id"),
                    )
                    away_team = Team.get_or_create_canonical(
                        name=row.get("away_team_name") or row.get("AwayTeam"),
                        api_id=row.get("away_team_api_id"),
                    )

                    # Date parsing
                    date_str = row.get("date") or row.get("Date")
                    date = parse_datetime(date_str)
                    if not date:
                        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                            try:
                                date = datetime.strptime(date_str, fmt)
                                break
                            except Exception:
                                continue

                    fixture_id = cls.canonical_fixture_id(home_team, away_team, league, season or "unknown", date)

                    cls.objects.update_or_create(
                        id=int(row.get("id", fixture_id.replace("-", ""))[:10]),
                        defaults={
                            "date": date,
                            "status": row.get("status", "scheduled"),
                            "league": league,
                            "season": season or "unknown",
                            "home_team": home_team,
                            "away_team": away_team,
                        },
                    )
                    imported += 1
                except Exception as e:
                    print(f"Skipping row due to error: {e} | Row: {row}")
                    continue
            print(f"✅ Imported {imported} fixtures from {file_path}")

    @classmethod
    def import_from_json(cls, file_path, league=None, season=None):
        # If league is a string, convert it to League instance for backward compatibility
        if isinstance(league, str):
            league = League.get_or_create_league(league)
        elif league is None:
            league = League.get_or_create_league("Premier League")
            
        with open(file_path, encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)
            imported = 0
            for item in data:
                try:
                    home_team = Team.get_or_create_canonical(
                        name=item.get("home_team_name") or item.get("HomeTeam"),
                        api_id=item.get("home_team_api_id"),
                    )
                    away_team = Team.get_or_create_canonical(
                        name=item.get("away_team_name") or item.get("AwayTeam"),
                        api_id=item.get("away_team_api_id"),
                    )

                    date_str = item.get("date") or item.get("Date")
                    date = parse_datetime(date_str)
                    if not date:
                        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                            try:
                                date = datetime.strptime(date_str, fmt)
                                break
                            except Exception:
                                continue

                    fixture_id = cls.canonical_fixture_id(home_team, away_team, league, season or "unknown", date)

                    cls.objects.update_or_create(
                        id=int(item.get("id", fixture_id.replace("-", ""))[:10]),
                        defaults={
                            "date": date,
                            "status": item.get("status", "scheduled"),
                            "league": league,
                            "season": season or "unknown",
                            "home_team": home_team,
                            "away_team": away_team,
                        },
                    )
                    imported += 1
                except Exception as e:
                    print(f"Skipping item due to error: {e} | Item: {item}")
                    continue
            print(f"✅ Imported {imported} fixtures from {file_path}")

# ------------------------------
# Players
# ------------------------------
class Player(models.Model):
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    season = models.CharField(max_length=50)
    position = models.CharField(
        max_length=50,
        choices=[
            ("GK", "Goalkeeper"),
            ("DEF", "Defender"),
            ("MID", "Midfielder"),
            ("FWD", "Forward"),
            ("UNK", "Unknown"),
        ],
        default="UNK",
    )
    injured = models.BooleanField(default=False)
    injury_type = models.CharField(max_length=100, blank=True, null=True)
    expected_return = models.DateField(blank=True, null=True)

    appearances = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)

    class Meta:
        unique_together = ["name", "team", "season"]

    def __str__(self):
        return f"{self.name} ({self.team} - {self.season})"

    @classmethod
    def import_from_csv(cls, csv_file_path, season=None):
        from utils.player_import import import_players_from_csv

        return import_players_from_csv(csv_file_path, season)


# ------------------------------
# Matches
# ------------------------------
class Match(models.Model):
    fixture_id = models.CharField(max_length=100, unique=True)
    home_team = models.ForeignKey(Team, related_name="home_matches", on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name="away_matches", on_delete=models.CASCADE)
    league = models.ForeignKey('League', on_delete=models.CASCADE, related_name='matches', null=True, blank=True)
    season = models.CharField(max_length=20)
    date = models.DateTimeField()
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    result = models.CharField(
        max_length=10, choices=[("win", "Win"), ("draw", "Draw"), ("loss", "Loss")], null=True, blank=True
    )

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name} ({self.season})"

    @staticmethod
    def canonical_fixture_id(home_team, away_team, league, season, date):
        return f"{league.code}-{season}-{home_team.id}-{away_team.id}-{date.date()}"

    @classmethod
    def import_from_csv(cls, file_path, league=None, season=None):
        # If league is a string, convert it to League instance for backward compatibility
        if isinstance(league, str):
            league = League.get_or_create_league(league)
        elif league is None:
            league = League.get_or_create_league("Premier League")
            
        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            imported = 0
            for row in reader:
                try:
                    home_team = Team.get_or_create_canonical(
                        name=row.get("HomeTeam") or row.get("Home Team"),
                        api_id=row.get("home_team_api_id"),
                    )
                    away_team = Team.get_or_create_canonical(
                        name=row.get("AwayTeam") or row.get("Away Team"),
                        api_id=row.get("away_team_api_id"),
                    )

                    date_str = row.get("Date")
                    date = parse_datetime(date_str)
                    if not date:
                        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                            try:
                                date = datetime.strptime(date_str, fmt)
                                break
                            except Exception:
                                continue

                    home_score = row.get("FTHG") or row.get("Home Score")
                    away_score = row.get("FTAG") or row.get("Away Score")

                    raw_result = (row.get("FTR") or row.get("Result", "")).strip()
                    result = RESULT_MAP.get(raw_result.upper()) or RESULT_MAP.get(raw_result.lower())

                    fixture_id = cls.canonical_fixture_id(home_team, away_team, league, season or "unknown", date)

                    cls.objects.update_or_create(
                        fixture_id=fixture_id,
                        defaults={
                            "home_team": home_team,
                            "away_team": away_team,
                            "league": league,
                            "season": season or "unknown",
                            "date": date,
                            "home_score": int(home_score) if home_score else None,
                            "away_score": int(away_score) if away_score else None,
                            "result": result,
                        },
                    )
                    imported += 1
                except Exception as e:
                    print(f"Skipping row due to error: {e} | Row: {row}")
                    continue
            print(f"✅ Imported {imported} matches from {file_path}")

# ------------------------------
# Predictions & User Bets
# ------------------------------
class Prediction(models.Model):
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE)
    result_pred = models.CharField(max_length=10, choices=[("win", "Win"), ("draw", "Draw"), ("loss", "Loss")])
    confidence = models.FloatField()
    goal_diff = models.IntegerField()
    fair_odds_home = models.FloatField()
    fair_odds_draw = models.FloatField()
    fair_odds_away = models.FloatField()
    model_version = models.CharField(max_length=20, default="v1")

    def __str__(self):
        return f"Prediction for {self.fixture}"


class UserPrediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE)
    predicted_result = models.CharField(
        max_length=10, choices=[("WIN", "Win"), ("DRAW", "Draw"), ("LOSE", "Lose")]
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "fixture")

    def __str__(self):
        return f"{self.user.username} → {self.fixture}: {self.predicted_result}"

class Bet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    predicted_result = models.CharField(max_length=10)
    amount = models.FloatField()
    odds = models.FloatField()
    is_settled = models.BooleanField(default=False)
    win = models.BooleanField(null=True, blank=True)
    payout = models.FloatField(default=0.0)
    placed_at = models.DateTimeField(auto_now_add=True)


# ------------------------------
# Gameweeks
# ------------------------------
class Gameweek(models.Model):
    number = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return f"GW {self.number}"


# ------------------------------
# Telegram Profiles
# ------------------------------
class TelegramProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="telegram_profile")
    telegram_id = models.CharField(max_length=50, unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.username or self.first_name} (tg:{self.telegram_id})"
        
        
# subscriptions
class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan_name = models.CharField(max_length=100)
    provider = models.CharField(max_length=50)
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    interval = models.CharField(max_length=20, default="monthly")
    status = models.CharField(max_length=20, default="inactive")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    telegram_id = models.CharField(max_length=50, null=True, blank=True)  # ✅ add this
    email = models.EmailField(null=True, blank=True)                        # ✅ add this
    metadata = models.JSONField(default=dict)


    def is_active(self):
        return self.status == "active"

    def __str__(self):
        return f"{self.user.username} - {self.plan_name} ({self.status})"