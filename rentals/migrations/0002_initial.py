# Generated by Django 5.1.4 on 2024-12-24 10:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('rentals', '0001_initial'),
        ('stations', '0001_initial'),
        ('vehicles', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalmodel',
            name='client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rentals', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='rentalmodel',
            name='pickup_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pickups', to='stations.stationmodel'),
        ),
        migrations.AddField(
            model_name='rentalmodel',
            name='return_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='returns', to='stations.stationmodel'),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='car',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vehicles.vehiclemodel'),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='pickup_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='stations.stationmodel'),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='return_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stations.stationmodel'),
        ),
    ]
