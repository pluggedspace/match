from django.utils.deprecation import MiddlewareMixin
from matches.models import UserSubscription

class SubscriptionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Attach to request instead of user
        request.has_active_subscription = False
        
        if request.user.is_authenticated:
            sub = UserSubscription.objects.filter(user=request.user, status="active").first()
            if sub:
                request.has_active_subscription = True