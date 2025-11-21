from django.apps import AppConfig

class MatchConfig(AppConfig):
    name = 'matches'

    def ready(self):
        # ✅ Import inside the function — safe timing
        from django.contrib.auth.models import User
        from matches.models import UserSubscription

        def has_active_subscription(self):
            try:
                return self.subscription.status == "active"
            except UserSubscription.DoesNotExist:
                return False

        # ✅ Dynamically add property to the User model
        User.add_to_class("has_active_subscription", property(has_active_subscription))