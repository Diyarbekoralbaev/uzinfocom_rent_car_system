# payments/utils.py
from .tasks import send_payment_email_task


def send_payment_email(payment_id):
    """
    Triggers the Celery task to send a payment receipt email.
    """
    send_payment_email_task.delay(payment_id)
