from rest_framework import serializers
from .models import VehicleModel, VehicleStatusChoices


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = [
            'id',
            'brand',
            'model',
            'daily_price',
            'status',
            'current_station',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'current_station': {'required': False, 'allow_null': True},
            'status': {'required': False},
        }


class VehicleAvailabilitySerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=VehicleStatusChoices.choices)

    class Meta:
        model = VehicleModel
        fields = ['id', 'status']
        read_only_fields = ['id']