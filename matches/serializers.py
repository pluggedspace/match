# matches/serializers.py
from rest_framework import serializers
from matches.models import Prediction, Match, Fixture, Gameweek, League

class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = ['id', 'name', 'code', 'country', 'logo_url']


class MatchSerializer(serializers.ModelSerializer):
    league = LeagueSerializer(read_only=True)

    class Meta:
        model = Match
        fields = ['id', 'home_team', 'away_team', 'match_date', 'league']


class PredictionSerializer(serializers.ModelSerializer):
    league = serializers.CharField(source='match.league.name', read_only=True)

    class Meta:
        model = Prediction
        fields = [
            'result_pred', 'confidence', 'goal_diff',
            'fair_odds_home', 'fair_odds_draw', 'fair_odds_away',
            'model_version', 'league'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # sanitize floats
        for key in ['confidence', 'goal_diff', 'fair_odds_home', 'fair_odds_draw', 'fair_odds_away']:
            val = data.get(key)
            if val is not None:
                try:
                    f = float(val)
                    if f == float('inf') or f == float('-inf') or f != f:
                        data[key] = None
                    else:
                        data[key] = f
                except (ValueError, TypeError):
                    data[key] = None
        return data


class FixtureSerializer(serializers.ModelSerializer):
    home_team = serializers.CharField(source='home_team.name')
    away_team = serializers.CharField(source='away_team.name')
    predictions = serializers.SerializerMethodField()
    league = LeagueSerializer(read_only=True)

    class Meta:
        model = Fixture
        fields = ['id', 'home_team', 'away_team', 'date', 'league', 'predictions']

    def get_predictions(self, obj):
        preds = getattr(obj, 'predictions', None)
        if preds is None:
            preds = list(obj.prediction_set.all())
        return PredictionSerializer(preds, many=True).data


class GameweekSerializer(serializers.ModelSerializer):
    fixtures = serializers.SerializerMethodField()

    class Meta:
        model = Gameweek
        fields = ['number', 'start_date', 'end_date', 'fixtures']

    def get_fixtures(self, obj):
        fixtures = getattr(obj, 'fixtures', None)
        if fixtures is None:
            fixtures = obj.fixture_set.all()
        return FixtureSerializer(fixtures, many=True).data