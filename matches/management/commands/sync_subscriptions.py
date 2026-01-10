# matches/management/commands/sync_subscriptions.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from matches.models import UserSubscription
from matches.utils.payments import get_user_subscription

User = get_user_model()

class Command(BaseCommand):
    help = "Sync user subscriptions from the configured payments API"

    def handle(self, *args, **kwargs):
        for user in User.objects.all():
            data = get_user_subscription(user.email)
            if not data:
                continue

            UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    "reference": data.get("reference"),
                    "plan_name": data.get("plan_name"),
                    "status": data.get("status"),
                    "interval": data.get("interval"),
                    "amount": data.get("amount") or 0,
                    "currency": data.get("currency") or "NGN",
                },
            )
            self.stdout.write(f"✅ Synced {user.email}: {data.get('plan_name')} ({data.get('status')})")