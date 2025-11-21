# telegrambot/subscribe.py

import logging
import requests
import asyncio
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from django.conf import settings
from matches.models import TelegramProfile, UserSubscription
from .utils import get_or_create_telegram_user
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)
API_BASE = f"{settings.BASE_URL}/api/subscriptions/start/"
VERIFY_RETRIES = 5
VERIFY_DELAY = 15  # seconds between retries

# ---------------- UTILITIES ----------------
def short_token(value: str) -> str:
    """Generate a short hash token for long/sensitive data."""
    return hashlib.sha1(value.encode()).hexdigest()[:10]


# ---------- STEP 1: COMMAND ENTRY ----------
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await sync_to_async(get_or_create_telegram_user)(tg_user)

    try:
        email = context.args[0]
    except IndexError:
        await update.message.reply_text(
            "📩 Please provide your email: `/subscribe your@email.com`",
            parse_mode="Markdown",
        )
        return

    # Store email mapping using short token
    email_token = short_token(email)
    if "email_map" not in context.user_data:
        context.user_data["email_map"] = {}
    context.user_data["email_map"][email_token] = email

    keyboard = [
        [InlineKeyboardButton("💳 Paystack", callback_data=f"provider|paystack|{email_token}")],
        [InlineKeyboardButton("🌍 Flutterwave", callback_data=f"provider|flutterwave|{email_token}")],
    ]
    await update.message.reply_text(
        "Choose your payment provider:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- STEP 2: HANDLE PROVIDER SELECTION ----------
async def provider_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Received callback data: {query.data}")
    
    try:
        data = query.data.split("|")
        if len(data) != 3:
            logger.error(f"Invalid callback data format: {query.data}")
            await query.message.reply_text("⚠️ Invalid provider selection.")
            return

        provider = data[1]
        email_token = data[2]
        email = context.user_data.get("email_map", {}).get(email_token)
        
        if not email:
            logger.error(f"Email not found for token: {email_token}")
            await query.message.reply_text("⚠️ Session expired. Please /subscribe again.")
            return

        logger.info(f"Processing provider selection: {provider} for email: {email}")

        if provider == "paystack":
            # Paystack → NGN only
            await initiate_subscription(query, provider, email, "NGN")
            return

        # Flutterwave → show currency options
        currencies = ["NGN", "USD", "GHS", "KES", "ZAR", "GBP", "EUR"]
        keyboard = [
            [InlineKeyboardButton(cur, callback_data=f"currency|{provider}|{email_token}|{cur}")]
            for cur in currencies
        ]
        await query.message.reply_text(
            "🌍 Select your preferred currency:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        logger.error(f"Error in provider_choice_callback: {e}")
        await query.message.reply_text("⚠️ An error occurred. Please try again.")


# ---------- STEP 3: HANDLE CURRENCY SELECTION ----------
async def currency_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Received currency callback data: {query.data}")
    
    try:
        data = query.data.split("|")
        if len(data) != 4:
            logger.error(f"Invalid currency callback data format: {query.data}")
            await query.message.reply_text("⚠️ Invalid currency selection.")
            return

        provider = data[1]
        email_token = data[2]
        currency = data[3]

        email = context.user_data.get("email_map", {}).get(email_token)
        if not email:
            await query.message.reply_text("⚠️ Session expired. Please /subscribe again.")
            return

        logger.info(f"Processing currency selection: {currency} for provider: {provider}")
        await initiate_subscription(query, provider, email, currency)

    except Exception as e:
        logger.error(f"Error in currency_choice_callback: {e}")
        await query.message.reply_text("⚠️ An error occurred. Please try again.")


# ---------- STEP 4: INITIATE SUBSCRIPTION ----------
async def initiate_subscription(query, provider, email, currency):
    tg_user = query.from_user
    user = await sync_to_async(get_or_create_telegram_user)(tg_user)

    try:
        profile = await sync_to_async(TelegramProfile.objects.get)(user=user)
        telegram_id = profile.telegram_id
    except TelegramProfile.DoesNotExist:
        await query.message.reply_text("⚠️ Telegram profile not found.")
        return

    payload = {
        "amount": 1000,  # Base NGN amount (auto-converted in backend)
        "currency": currency,
        "provider": provider,
        "interval": "monthly",
        "plan_name": "MatchBot Premium",
        "telegram_id": telegram_id,
        "email": email,
    }

    headers = {"Content-Type": "application/json"}

    try:
        logger.info(f"Initiating subscription with payload: {payload}")
        resp = requests.post(API_BASE, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        payment_url = (
            data.get("data", {}).get("authorization_url")
            or data.get("payment_link")
            or data.get("redirect_url")
        )
        reference = (
            data.get("data", {}).get("reference")
            or data.get("reference")
        )

        if not payment_url or not reference:
            logger.error(f"No payment URL or reference in response: {data}")
            await query.message.reply_text("❌ Could not generate payment link.")
            return

        # Save subscription
        await sync_to_async(UserSubscription.objects.update_or_create)(
            reference=reference,
            defaults={
                "user": user,
                "plan_name": payload["plan_name"],
                "amount": payload["amount"],
                "currency": payload["currency"],
                "interval": payload["interval"],
                "status": "pending",
                "provider": payload["provider"],
                "telegram_id": telegram_id,
                "email": email,
                "metadata": {"telegram_id": telegram_id, "email": email},
            },
        )

        # Send payment link
        keyboard = [[InlineKeyboardButton("💳 Pay Now", url=payment_url)]]
        markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"You're using *{provider.title()}* in *{currency}*. Click below to pay:",
            parse_mode="Markdown",
            reply_markup=markup,
        )

        # Start verification in background
        asyncio.create_task(verify_subscription_status(query, reference))

    except requests.RequestException as e:
        logger.error(f"Payment initiation failed: {e}")
        await query.message.reply_text("⚠️ Unable to initiate subscription. Try again later.")
    except Exception as e:
        logger.error(f"Unexpected error in initiate_subscription: {e}")
        await query.message.reply_text("⚠️ An unexpected error occurred. Please try again.")


# ---------- STEP 5: VERIFY PAYMENT STATUS ----------
async def verify_subscription_status(query, reference):
    verify_url = f"https://payments.pluggedspace.org/api/payments/verify/{reference}/"
    status = "pending"
    verify_data = {}

    logger.info(f"Starting verification for reference: {reference}")

    for attempt in range(VERIFY_RETRIES):
        try:
            logger.info(f"Verification attempt {attempt + 1} for {reference}")
            verify_resp = requests.get(
                verify_url,
                headers={"X-API-KEY": settings.PLUGGEDSPACE_API_KEY},
                timeout=10,
            )
            verify_resp.raise_for_status()
            verify_data = verify_resp.json()
            status = verify_data.get("status", "pending")

            logger.info(f"Verification attempt {attempt + 1}: status = {status}")

            if status.lower() in ["success", "failed", "cancelled"]:
                break

        except requests.RequestException as e:
            logger.warning(f"Verify attempt {attempt+1} failed: {e}")

        await asyncio.sleep(VERIFY_DELAY)

    try:
        await sync_to_async(UserSubscription.objects.filter(reference=reference).update)(
            status=status,
            metadata=verify_data
        )

        if status.lower() == "success":
            await query.message.reply_text("✅ Payment confirmed! Your MatchBot Premium is now active.")
        elif status.lower() in ["failed", "cancelled"]:
            await query.message.reply_text("❌ Payment failed or cancelled. Please try again.")
        else:
            await query.message.reply_text("⚠️ Payment still pending. Check back later.")
            
    except Exception as e:
        logger.error(f"Error updating subscription status: {e}")


# ---------- REGISTER HANDLERS ----------
def register_subscribe_handlers(application):
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CallbackQueryHandler(provider_choice_callback, pattern=r"^provider\|"))
    application.add_handler(CallbackQueryHandler(currency_choice_callback, pattern=r"^currency\|"))