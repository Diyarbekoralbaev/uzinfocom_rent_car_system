from random import randint
from django.core.mail import send_mail

from uzinfocom_rent_car_system_drf.settings import DEFAULT_FROM_EMAIL


def generate_otp():
    random = randint(1000, 9999)
    return random


def send_otp_email(email, otp):
    send_mail(
        subject='Welcome to Rent Car System',
        message=f'Your OTP is: {otp}',
        from_email=DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

