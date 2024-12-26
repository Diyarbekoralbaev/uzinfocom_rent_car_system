from random import randint
from django.core.mail import send_mail

from uzinfocom_rent_car_system_drf.settings import DEFAULT_FROM_EMAIL, ESKIZ_EMAIL, ESKIZ_PASSWORD

from eskiz.client.sync import ClientSync

eskiz_client= ClientSync(
    email=ESKIZ_EMAIL,
    password=ESKIZ_PASSWORD
)

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

def send_sms_otp(phone, otp):
    eskiz_client.send_sms(
        phone_number=phone,
        message=f'Your OTP is: {otp}'
    )
