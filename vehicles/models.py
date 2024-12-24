from django.db import models

class VehicleStatusChoices(models.TextChoices):
    AVAILABLE = 'AV', 'Available'
    RENTED = 'RT', 'Rented'
    MAINTENANCE = 'MN', 'Maintenance'

class VehicleModel(models.Model):
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    daily_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=VehicleStatusChoices.choices, default=VehicleStatusChoices.AVAILABLE)
    current_station = models.ForeignKey('stations.StationModel', on_delete=models.CASCADE, related_name='vehicles', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f'{self.brand} {self.model}'