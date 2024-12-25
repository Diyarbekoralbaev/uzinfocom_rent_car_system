from django.db import models

from stations.models import StationModel
from users.models import UserModel
from vehicles.models import VehicleModel


class RentalStatusChoices(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACTIVE = 'ACTIVE', 'Active'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ReservationStatusChoices(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class RentalModel(models.Model):
    client = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name='rentals', db_index=True
    )
    car = models.ForeignKey(
        VehicleModel, on_delete=models.CASCADE, related_name='rentals', db_index=True
    )
    pickup_station = models.ForeignKey(
        StationModel,
        on_delete=models.CASCADE,
        related_name='pickups',
        null=True,
        blank=True,
        db_index=True
    )
    return_station = models.ForeignKey(
        StationModel,
        on_delete=models.CASCADE,
        related_name='returns',
        null=True,
        blank=True,
        db_index=True
    )
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=RentalStatusChoices.choices,
        default=RentalStatusChoices.PENDING,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['car', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Rental {self.id} - {self.client.username} - {self.car}"

    def can_transition_to(self, new_status):
        valid_transitions = {
            RentalStatusChoices.PENDING: [RentalStatusChoices.ACTIVE, RentalStatusChoices.CANCELLED],
            RentalStatusChoices.ACTIVE: [RentalStatusChoices.COMPLETED, RentalStatusChoices.CANCELLED],
            RentalStatusChoices.COMPLETED: [],
            RentalStatusChoices.CANCELLED: []
        }
        return new_status in valid_transitions.get(self.status, [])


class ReservationModel(models.Model):
    client = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name='reservations', db_index=True
    )
    car = models.ForeignKey(
        VehicleModel, on_delete=models.CASCADE, related_name='reservations', db_index=True
    )
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ReservationStatusChoices.choices,
        default=ReservationStatusChoices.PENDING,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'car', 'status']),
            models.Index(fields=['car', 'start_date', 'end_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Reservation {self.id} - {self.client.username} - {self.car}"
