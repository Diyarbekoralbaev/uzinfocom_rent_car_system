from django.db import models

class RentalModel(models.Model):
    client = models.ForeignKey('users.UserModel', on_delete=models.CASCADE, related_name='rentals')
    car = models.ForeignKey('vehicles.VehicleModel', on_delete=models.CASCADE)
    pickup_station = models.ForeignKey('stations.StationModel', on_delete=models.CASCADE, related_name='pickups', null=True, blank=True)
    return_station = models.ForeignKey('stations.StationModel', on_delete=models.CASCADE, related_name='returns', null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Rental {self.id} - {self.client.username} - {self.car}"


class ReservationModel(models.Model):
    client = models.ForeignKey('users.UserModel', on_delete=models.CASCADE)
    car = models.ForeignKey('vehicles.VehicleModel', on_delete=models.CASCADE)
    pickup_station = models.ForeignKey('stations.StationModel', on_delete=models.CASCADE, related_name='reservations')
    return_station = models.ForeignKey('stations.StationModel', on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reservation {self.id} - {self.client.username} - {self.car}"