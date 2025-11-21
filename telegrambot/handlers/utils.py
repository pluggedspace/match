# utils.py
import re
from django.contrib.auth.models import User
from matches.models import TelegramProfile

def get_or_create_telegram_user(telegram_user):
    username = f"tg_{telegram_user.id}"

    # ✅ Get or create User
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": telegram_user.first_name or "",
            "last_name": telegram_user.last_name or "",
            "email": "",
        }
    )
    if not user.has_usable_password():
        user.set_unusable_password()
        user.save()

    # ✅ Get or create TelegramProfile
    profile, created = TelegramProfile.objects.get_or_create(
        telegram_id=str(telegram_user.id),
        defaults={
            "username": telegram_user.username,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name,
            "user": user,
        }
    )

    if not created:
        # keep profile in sync if user changes Telegram details
        profile.username = telegram_user.username
        profile.first_name = telegram_user.first_name
        profile.last_name = telegram_user.last_name
        profile.save()

    return user

def parse_teams_from_text(text: str):
    match = re.search(r"between ([\w\s]+) and ([\w\s]+)", text, re.IGNORECASE)
    if match:
        team_a = match.group(1).strip()
        team_b = match.group(2).strip()
        return team_a, team_b
    return None, None