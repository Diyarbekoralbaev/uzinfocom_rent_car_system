# Generated by Django 5.1.4 on 2024-12-25 06:42

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_initial'),
        ('rentals', '0004_alter_rentalmodel_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Payment',
            new_name='PaymentModel',
        ),
    ]
