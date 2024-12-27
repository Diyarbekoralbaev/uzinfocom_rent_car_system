import requests
from celery import shared_task
from django.core.mail import send_mail

from uzinfocom_rent_car_system_drf import settings
from .models import UserModel


@shared_task
def send_otp_email_task(email, otp):
    """
    Send an OTP to the user's email
    :param email: User's email
    :param otp: OTP
    """
    send_mail(
        subject='Welcome to Rent Car System',
        message=f'Your OTP is: {otp}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task
def send_sms_otp_task(phone, otp):
    """
    Send an OTP to the user's phone number using Infobip
    :param phone: User's phone number
    :param otp: OTP
    """
    url = f"{settings.INFOBIP_BASE_URL}{settings.INFOBIP_SMS_ENDPOINT}"
    payload = {
        "messages": [
            {
                "destinations": [{"to": phone}],
                "from": settings.INFOBIP_SENDER,
                "text": f"WELCOME TO RENT CAR SYSTEM. Your OTP is: {otp}"
            }
        ]
    }
    headers = {
        'Authorization': f'App {settings.INFOBIP_API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        # Optionally, you can log or handle the response data here
        print("SMS sent successfully:", data)
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # Log the error
    except Exception as err:
        print(f"An error occurred: {err}")  # Log the error


@shared_task
def send_email_notifications_task(user_id, subject, message):
    """
    Send an email notification to the user
    :param user_id: User ID
    :param subject: Email subject
    :param message: Email message
    """
    try:
        user = UserModel.objects.get(id=user_id)
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except UserModel.DoesNotExist:
        print(f"User with id {user_id} does not exist.")
