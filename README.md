# Match Bot

## About

Match Bot is a sophisticated **Machine Learning-powered Match Prediction Engine**. It leverages historical data and advanced algorithms to predict match outcomes with high accuracy. The system is fully integrated with Telegram for delivering predictions and managing user subscriptions.

**Key Features:**
- **ML Prediction Engine**: Uses advanced machine learning models to analyze and predict match results.
- **Telegram Integration**: Seamless interaction for users directly within Telegram.
- **Subscription Management**: Supports monthly/yearly subscriptions with automated expiration and renewal tracking.
- **Multi-Provider Payments**: Integrated with **Paystack** (NGN) and **Flutterwave** (Multi-currency: USD, GHS, KES, etc.) for flexible payment options.
- **Scalable Storage**: Configured to work with AWS S3 or Backblaze B2 for handling media assets.
- **Background Tasks**: Utilizes Celery and Redis for efficient off-loading of heavy tasks like subscription syncing and notifications.
- **Secure Architecture**: Built with security best practices, including environment-based configuration and secure payment verification.

## Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (for Celery)

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd match
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**

    Copy `.env.example` to `.env`:

    ```bash
    cp .env.example .env
    ```

    Open `.env` and fill in your configuration details:
    - Database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`, etc.)
    - API Keys (`PLUGGEDSPACE_API_KEY`, `TELEGRAM_BOT_API_KEY`)
    - Sentry DSN (optional)
    - AWS/S3 credentials (if using cloud storage)

5.  **Run Migrations:**

    ```bash
    python manage.py migrate
    ```

6.  **Start the Development Server:**

    ```bash
    python manage.py runserver
    ```

## Celery Setup

To run the Celery worker for background tasks:

```bash
celery -A match worker -l info
```

## License

This project is free for non-commercial use. Commercial use requires explicit permission from the author.
See the [LICENSE](LICENSE) file for details.
