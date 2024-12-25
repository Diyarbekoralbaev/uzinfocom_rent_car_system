# Generated by Django 5.1.4 on 2024-12-24 10:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0002_initial'),
        ('stations', '0002_alter_stationmodel_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rentalmodel',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='rentalmodel',
            name='pickup_station',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pickups', to='stations.stationmodel'),
        ),
        migrations.AlterField(
            model_name='rentalmodel',
            name='return_station',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='returns', to='stations.stationmodel'),
        ),
        migrations.AlterField(
            model_name='rentalmodel',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]