from random import randint
from .tasks import send_otp_email_task, send_sms_otp_task, send_email_notifications_task


def generate_otp():
    """
    Generate a random 4-digit OTP
    :return: 4-digit OTP
    """
    random = randint(1000, 9999)
    return random


def send_otp_email(email, otp):
    """
    Send an OTP to the user's email
    :param email: User's email
    :param otp: OTP
    """
    send_otp_email_task.delay(email, otp)


def send_sms_otp(phone, otp):
    """
    Send an OTP to the user's phone number
    :param phone: User's phone number
    :param otp: OTP
    """
    send_sms_otp_task.delay(phone, otp)


def send_registration_confirmation_email(user_id):
    """
    Send an email confirmation to the user after registration
    :param user_id: User ID
    """
    subject = 'Registration Confirmation'
    message = 'You have successfully registered.'
    send_email_notifications_task.delay(user_id, subject, message)

def send_password_change_notification(user_id):
    """
    Send an email notification to the user after changing the password
    :param user_id: User ID
    """
    subject = 'Password Changed'
    message = 'Your password has been changed successfully.'
    send_email_notifications_task.delay(user_id, subject, message)


def send_password_reset_notification(user_id):
    """
    Send an email notification to the user after resetting the password
    :param user_id: User ID
    """
    subject = 'Password Reset'
    message = 'Your password has been reset successfully.'
    send_email_notifications_task.delay(user_id, subject, message)
