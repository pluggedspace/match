# matches/urls
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from matches.views import PredictionViewSet, retrain_predictions, LeagueViewSet, CurrentGameweekAPIView, check_subscription
from matches.views_dashboard import (
    prediction_overview,
    prediction_confidence_distribution,
    latest_predictions,
    compare_versions,
)
from matches.views_ui import predictions_template_view
from .views_landing import LandingPageView
from matches.subscriptions import views as subs_views

# Router registration for ViewSets
router = DefaultRouter()
router.register(r'predictions', PredictionViewSet, basename='prediction')
router.register(r'leagues', LeagueViewSet, basename='league')  # Fixed: removed space

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    # ViewSet-based API endpoints
    path('api/', include(router.urls)),

    # Function-based API views
    path('api/retrain/', retrain_predictions, name='retrain_predictions'),
    path('api/dashboard/overview/', prediction_overview, name='dashboard_overview'),
    path('api/dashboard/confidence/', prediction_confidence_distribution, name='dashboard_confidence'),
    path('api/predictions/latest/', latest_predictions, name='latest_predictions'),
    path('api/dashboard/compare_versions/', compare_versions, name='compare_versions'),

    # UI endpoint
    path('dashboard/predictions/', predictions_template_view, name='predictions_template_view'),
    
    # Current gameweek endpoint
    path('api/current-gameweek/', CurrentGameweekAPIView.as_view(), name='current_gameweek'),  # Fixed: consistent naming

    path("api/subscriptions/start/", subs_views.StartSubscriptionView.as_view(), name="start-subscription"),
    #path("api/subscriptions/callback/", subs_views.subscription_callback, name="subscription-callback"),
    
    path("api/check-subscription/<str:tg_id>/", check_subscription, name="check-subscription"),
]