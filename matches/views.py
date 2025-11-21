# matches/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.timezone import now

from matches.models import Prediction, Match, Gameweek, Fixture, League
from matches.serializers import (
    PredictionSerializer,
    GameweekSerializer,
    LeagueSerializer
)
from matches.logic.train_and_predict import train_and_predict

from rest_framework.permissions import BasePermission

class HasActiveSubscriptionOrFreeAccess(BasePermission):
    message = "You need an active subscription for full access."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # ✅ Free access: allow viewing limited data
        if not request.user.has_active_subscription:
            view.free_access = True
            return True

        view.free_access = False
        return True


class LeagueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of all leagues.
    """
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    

class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PredictionSerializer
    permission_classes = [HasActiveSubscriptionOrFreeAccess]

    def get_queryset(self):
        queryset = Prediction.objects.select_related('fixture', 'fixture__league')
        league_code = self.request.query_params.get('league')

        if league_code:
            queryset = queryset.filter(fixture__league__code__iexact=league_code)

        # ✅ Free users only see first 5 predictions or specific leagues
        if getattr(self, "free_access", False):
            return queryset.order_by('-fixture__date')[:5]  # limit to 5 free
        return queryset

    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        upcoming_fixtures = Fixture.objects.filter(status="scheduled").order_by("date")
        predictions = self.get_queryset().filter(fixture__in=upcoming_fixtures)
        serializer = self.get_serializer(predictions, many=True)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def retrain_predictions(request):
    result = train_and_predict()

    if result['status'] == "fail":
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    return Response(result, status=status.HTTP_200_OK)


class CurrentGameweekAPIView(APIView):
    """
    Returns the current gameweek and its fixtures with predictions
    """
    def get(self, request, format=None):
        today = now()
        gw = Gameweek.objects.filter(start_date__lte=today, end_date__gte=today).first()
        if not gw:
            return Response({"detail": "No active gameweek found."}, status=status.HTTP_404_NOT_FOUND)

        fixtures = Fixture.objects.filter(date__range=(gw.start_date, gw.end_date)) \
                                  .select_related('home_team', 'away_team', 'league') \
                                  .prefetch_related('prediction_set')

        gw.fixtures = fixtures
        serializer = GameweekSerializer(gw)
        return Response(serializer.data)
        

@api_view(['GET'])
def check_subscription(request, tg_id):
    from matches.models import TelegramProfile
    try:
        profile = TelegramProfile.objects.select_related('user').get(telegram_id=tg_id)
        return Response({"active": profile.user.has_active_subscription})
    except TelegramProfile.DoesNotExist:
        return Response({"active": False})