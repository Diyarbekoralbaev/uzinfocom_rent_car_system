from django.db import models

class VehicleStatusChoices(models.TextChoices):
    AVAILABLE = 'AV', 'Available'
    RENTED = 'RT', 'Rented'
    MAINTENANCE = 'MN', 'Maintenance'


class VehicleModel(models.Model):
    brand = models.CharField(max_length=50, db_index=True)
    model = models.CharField(max_length=50)
    daily_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=2,
        choices=VehicleStatusChoices.choices,
        default=VehicleStatusChoices.AVAILABLE,
        db_index=True
    )
    current_station = models.ForeignKey(
        'stations.StationModel',
        on_delete=models.CASCADE,
        related_name='vehicles',
        null=True,
        blank=True,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['brand']),
            models.Index(fields=['current_station']),
        ]
        ordering = ['brand', 'model']

    def __str__(self):
        return f'{self.brand} {self.model}'