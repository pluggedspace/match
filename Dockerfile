# Dockerfile

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt
# Install PostgreSQL client tools (for pg_dump, psql, etc.)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy the whole project
COPY . .

# Explicitly copy the model file to ensure it's inside the image
# (optional if it's already inside your project folder copied by COPY . .)
COPY matches/models/ml_model.pkl /app/matches/models/ml_model.pkl


CMD ["gunicorn", "match.wsgi:application", "--bind", "0.0.0.0:8001"]