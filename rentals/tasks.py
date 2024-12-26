from django.conf import settings
from django.core.mail import send_mail
from celery import shared_task
from users.models import UserModel


@shared_task
def send_email_notifications_task(user_id, subject, message):
    """
    Send email notifications to the user.
    """
    user = UserModel.objects.get(pk=user_id)
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )