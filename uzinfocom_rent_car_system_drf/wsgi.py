"""
WSGI config for uzinfocom_rent_car_system_drf project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uzinfocom_rent_car_system_drf.settings')

application = get_wsgi_application()
