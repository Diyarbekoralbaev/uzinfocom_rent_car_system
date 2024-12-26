from math import radians, sin, cos, sqrt, atan2

from django.conf import settings
from django.core.mail import send_mail
from .tasks import send_email_notifications_task


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points 
    on the Earth specified by latitude and longitude using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Radius of the Earth in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance


def is_near_station(user_lat, user_lon, station_lat, station_lon, max_distance=settings.MAX_DISTANCE):
    """
    Determine if the user is within `max_distance` kilometers of the station.
    :param user_lat: User's latitude
    :param user_lon: User's longitude
    :param station_lat: Station's latitude
    :param station_lon: Station's longitude
    :param max_distance: Maximum distance in kilometers
    :return: True if the user is near the station, False otherwise
    """
    distance = calculate_distance(user_lat, user_lon, station_lat, station_lon)
    return distance <= max_distance


def send_email_notification(user_id, subject, message):
    """
    Send email notifications to the user.
    :param user_id: User ID
    :param subject: Email subject
    :param message: Email message
    """
    send_email_notifications_task.delay(user_id, subject, message)