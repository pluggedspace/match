# match/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'match.settings')

app = Celery('match')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()