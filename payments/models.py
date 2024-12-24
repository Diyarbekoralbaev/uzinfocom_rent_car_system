from django.db import models

class Payment(models.Model):
    user = models.ForeignKey('users.UserModel', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20, choices=[
        ('DEPOSIT', 'Balance Deposit'),
        ('RENTAL', 'RentalModel Payment')
    ])
    rental = models.ForeignKey('rentals.RentalModel', on_delete=models.CASCADE, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']