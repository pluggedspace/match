# matches/utils/payments.py
import requests
from django.conf import settings

PAYMENTS_API_BASE = getattr(settings, "PAYMENTS_API_BASE", "https://payments.pluggedspace.org/api")
PLUGGEDSPACE_API_KEY = getattr(settings, "PLUGGEDSPACE_API_KEY", "")

def get_user_subscription(email: str):
    headers = {"Authorization": f"Bearer {PLUGGEDSPACE_API_KEY}"}
    url = f"{PAYMENTS_API_BASE}/subscriptions/?email={email}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]
    except Exception as e:
        print(f"[Subscription Sync Error] {e}")
    return None