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
            'current_station': {'required': True, 'allow_null': True},
            'status': {'required': False},
        }

    def validate_daily_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Daily price must be a positive number.")
        return value

    def validate_current_station(self, value):
        if not value:
            raise serializers.ValidationError("Current station is required.")
        return value


class VehicleAvailabilitySerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=VehicleStatusChoices.choices)

    class Meta:
        model = VehicleModel
        fields = ['id', 'status']
        read_only_fields = ['id']