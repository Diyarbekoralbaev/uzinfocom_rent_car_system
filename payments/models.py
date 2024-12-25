import uuid

from django.db import models


class PaymentStatusChoices(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class PaymentModel(models.Model):
    user = models.ForeignKey(
        'users.UserModel',
        on_delete=models.CASCADE,
        related_name='payments',
        db_index=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_time = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatusChoices.choices,
        default=PaymentStatusChoices.PENDING,
        db_index=True
    )
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )

    class Meta:
        ordering = ['-payment_time']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_id']),
        ]

    def __str__(self):
        return f"Payment #{self.transaction_id} for {self.user} - {self.status}"
