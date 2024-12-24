from django.db import models
from django.contrib.auth.models import AbstractUser


class UserChoice(models.TextChoices):
    CLIENT = 'CL', 'Client'
    MANAGER = 'MN', 'Manager'

class UserModel(AbstractUser):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    role = models.CharField(max_length=2, choices=UserChoice.choices, default=UserChoice.CLIENT)
    is_verified = models.BooleanField(default=False)
