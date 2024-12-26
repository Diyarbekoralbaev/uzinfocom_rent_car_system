from celery import shared_task
from django.core.mail import send_mail
from eskiz.client.sync import ClientSync

from uzinfocom_rent_car_system_drf.settings import DEFAULT_FROM_EMAIL, ESKIZ_EMAIL, ESKIZ_PASSWORD
from .models import UserModel

eskiz_client = ClientSync(
    email=ESKIZ_EMAIL,
    password=ESKIZ_PASSWORD
)


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
        from_email=DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task
def send_sms_otp_task(phone, otp):
    """
    Send an OTP to the user's phone number
    :param phone: User's phone number
    :param otp: OTP
    """
    eskiz_client.send_sms(
        phone_number=phone,
        message=f'Your OTP is: {otp}'
    )


@shared_task
def send_email_notifications_task(user_id, subject, message):
    """
    Send an email notification to the user
    :param user_id: User ID
    :param subject: Email subject
    :param message: Email message
    """
    send_mail(
        subject=subject,
        message=message,
        from_email=DEFAULT_FROM_EMAIL,
        recipient_list=[UserModel.objects.get(id=user_id).email],
        fail_silently=False,
    )
