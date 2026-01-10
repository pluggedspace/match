# Match Bot

This is a Django-based project for the Match Bot service, including Telegram bot integration and S3 media storage support.

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
