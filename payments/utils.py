from django.core.mail import send_mail
from users.models import UserModel
from django.conf import settings

def send_payment_email(email, amount):
    user = UserModel.objects.get(email=email)
    send_mail(
        subject='Payment Received',
        message=f'Hi {user.first_name},\n\nYou have received a payment of ${amount}.\n\nThanks!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )