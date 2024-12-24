"""
ASGI config for uzinfocom_rent_car_system_drf project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uzinfocom_rent_car_system_drf.settings')

application = get_asgi_application()
