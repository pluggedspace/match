# matches/subscriptions/views.py
import requests
import uuid
from django.conf import settings
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.db import transaction
from matches.models import UserSubscription, TelegramProfile


def convert_amount(amount_ngn, target_currency):
    """
    Convert NGN to target_currency using exchangerate.host.
    Caches FX rates for 1 hour.
    """
    if target_currency == "NGN":
        return float(amount_ngn)

    target_currency = target_currency.upper()
    cache_key = f"fx_rate_NGN_{target_currency}"
    rate = cache.get(cache_key)

    if not rate:
        url = f"https://api.exchangerate.host/convert?from=NGN&to={target_currency}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("info", {}).get("rate")
            if not rate:
                raise ValueError("Invalid FX rate response")
            cache.set(cache_key, rate, timeout=3600)
        except Exception as e:
            raise ValueError(f"Failed to fetch exchange rate: {e}")

    converted = round(float(amount_ngn) * rate, 2)
    return converted


class StartSubscriptionView(APIView):
    """
    Starts a subscription and initiates hosted payment session.
    Auto-selects provider based on currency:
      - Paystack → NGN only
      - Flutterwave → multi-currency (USD, GHS, KES, ZAR, GBP, EUR, NGN)
    """

    @transaction.atomic
    def post(self, request):
        print("📥 Incoming subscription payload:", request.data)

        telegram_id = request.data.get("telegram_id")
        email = request.data.get("email")
        amount = request.data.get("amount")
        currency = request.data.get("currency", "NGN").upper()
        provider = request.data.get("provider")  # optional
        plan_name = request.data.get("plan_name", "MatchBot Premium")
        interval = request.data.get("interval", "monthly")

        if not telegram_id or not email or not amount:
            return Response(
                {"error": "telegram_id, email, and amount are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Resolve user
        try:
            profile = TelegramProfile.objects.get(telegram_id=telegram_id)
            user = profile.user
        except TelegramProfile.DoesNotExist:
            return Response(
                {"error": f"No user linked to telegram_id {telegram_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ✅ Auto-select or validate provider
        if not provider:
            if currency != "NGN":
                provider = "flutterwave"
            else:
                provider = "paystack"
        else:
            provider = provider.lower()

        if provider not in ["paystack", "flutterwave"]:
            return Response(
                {"error": "Invalid provider. Must be 'paystack' or 'flutterwave'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider == "paystack" and currency != "NGN":
            return Response(
                {"error": "Paystack only supports NGN. Use Flutterwave for other currencies."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Auto-convert amount if Flutterwave multi-currency
        base_amount = float(amount)
        if currency != "NGN" and provider == "flutterwave":
            try:
                converted = convert_amount(base_amount, currency)
                print(f"💱 Converted {base_amount} NGN → {converted} {currency}")
                amount = converted
            except Exception as e:
                return Response(
                    {"error": f"Currency conversion failed: {e}"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        # ✅ Check existing subscription
        active_sub = UserSubscription.objects.filter(user=user, status="active").first()
        if active_sub:
            return Response(
                {"message": "You already have an active subscription."},
                status=status.HTTP_200_OK,
            )

        # ✅ Generate unique reference
        reference = f"sub_{uuid.uuid4().hex[:8]}"

        payload = {
            "amount": amount,
            "currency": currency,
            "email": email,
            "reference": reference,
            "provider": provider,
            "customer_name": "MatchBot User",
            "phone": "08000000000",
            "callback_url": f"{settings.BASE_URL}/api/subscriptions/callback/",
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": settings.PLUGGEDSPACE_API_KEY,
        }

        try:
            resp = requests.post(
                f"{settings.PAYMENTS_API_BASE}/api/payments/initiate/",
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            response_data = resp.json()

            # ✅ Save pending subscription
            UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    "plan_name": plan_name,
                    "amount": amount,
                    "currency": currency,
                    "interval": interval,
                    "status": "pending",
                    "provider": provider,
                    "telegram_id": telegram_id,
                    "email": email,
                    "metadata": {"telegram_id": telegram_id, "email": email},
                    "reference": reference,
                },
            )

            return Response(response_data, status=resp.status_code)

        except requests.exceptions.RequestException as e:
            return Response(
                {"error": f"Payment service unavailable: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


@api_view(["POST"])
@transaction.atomic
def verify_subscription(request):
    """
    Verify a subscription status with Pluggedspace and update local record.
    Expects payload:
      { "reference": "sub_12ab34cd" }
    """
    reference = request.data.get("reference")
    if not reference:
        return Response(
            {"error": "Missing reference"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        sub = UserSubscription.objects.get(reference=reference)
    except UserSubscription.DoesNotExist:
        return Response(
            {"error": f"No subscription found for reference {reference}"},
            status=status.HTTP_404_NOT_FOUND
        )

    # ✅ Call Pluggedspace verify endpoint
    try:
        resp = requests.get(
            f"{settings.PAYMENTS_API_BASE}/api/payments/verify/{reference}/",
            headers={"X-API-KEY": settings.PLUGGEDSPACE_API_KEY},
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json()

        # Map provider response to our local model fields
        status_text = data.get("status") or sub.status
        sub.status = status_text
        sub.amount = data.get("amount", sub.amount)
        sub.currency = data.get("currency", sub.currency)
        sub.provider = data.get("provider", sub.provider)
        sub.metadata = data  # store full response for reference
        sub.save(update_fields=["status", "amount", "currency", "provider", "metadata"])

        return Response(
            {
                "message": f"Subscription {reference} updated to '{sub.status}'",
                "subscription": {
                    "reference": sub.reference,
                    "status": sub.status,
                    "amount": sub.amount,
                    "currency": sub.currency,
                    "provider": sub.provider,
                }
            },
            status=status.HTTP_200_OK
        )

    except requests.exceptions.RequestException as e:
        return Response(
            {"error": f"Failed to verify subscription: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )