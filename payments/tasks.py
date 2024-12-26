from datetime import datetime

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import PaymentModel
from users.models import UserModel


@shared_task
def send_payment_email_task(payment_id):
    try:
        payment = PaymentModel.objects.select_related('user').get(id=payment_id)
        user = payment.user

        subject = 'Payment Received'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]

        # Render the HTML template with context
        html_content = render_to_string('payments/payment_receipt.html', {
            'user': user,
            'payment': payment,
            'current_year': datetime.now().year,
        })

        # Create the email
        email = EmailMultiAlternatives(subject, '', from_email, to_email)
        email.attach_alternative(html_content, "text/html")

        # Send the email
        email.send(fail_silently=False)

    except PaymentModel.DoesNotExist:
        pass
    except Exception as e:
        pass
