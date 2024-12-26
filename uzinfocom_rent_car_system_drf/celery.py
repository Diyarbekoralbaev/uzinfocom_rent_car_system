import os
from celery import Celery

# Set the default settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uzinfocom_rent_car_system_drf.settings')

app = Celery('uzinfocom_rent_car_system_drf')

# Load Celery settings from Django settings using the 'CELERY_' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover and load tasks from all installed apps
app.autodiscover_tasks()
