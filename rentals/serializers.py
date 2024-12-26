from django.utils import timezone
from rest_framework import serializers

from vehicles.models import VehicleStatusChoices
from .models import RentalModel, ReservationModel


class RentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalModel
        fields = [
            'id', 'client', 'car', 'pickup_station', 'return_station',
            'start_date', 'end_date', 'total_amount', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'client', 'status', 'total_amount',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'start_date': {'required': True},
            'end_date': {'required': True},
            'pickup_station': {'required': True},
            'return_station': {'required': False},
        }

    def validate(self, data):
        """
        Validate date logic:
          - end_date > start_date
          - start_date >= now()
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date is not None and end_date is not None:
            if start_date >= end_date:
                raise serializers.ValidationError("End date must be greater than start date.")
            if start_date < timezone.now():
                raise serializers.ValidationError("Cannot rent a car in the past.")

        return data

    def validate_car(self, value):
        """Ensure the car is available."""
        if value.status != VehicleStatusChoices.AVAILABLE:
            raise serializers.ValidationError("Vehicle is not available.")
        return value

    def validate_pickup_station(self, value):
        """Ensure the pickup station is active."""
        if not value.is_active:
            raise serializers.ValidationError("Pickup station is not active.")
        return value

    def validate_return_station(self, value):
        """Ensure the return station is active if specified."""
        if value and not value.is_active:
            raise serializers.ValidationError("Return station is not active.")
        return value


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationModel
        fields = [
            'id', 'client', 'car', 'start_date', 'end_date',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'client', 'status', 'created_at', 'updated_at'
        ]

    def validate_client(self, value):
        """Ensure only clients can make reservations."""
        if value.role != 'CLIENT':
            raise serializers.ValidationError("Only clients can reserve vehicles.")
        if not value.is_verified:
            raise serializers.ValidationError("Client not verified.")
        return value

    def validate_car(self, value):
        """Ensure the car is available."""
        if value.status != VehicleStatusChoices.AVAILABLE:
            raise serializers.ValidationError("Vehicle is not available.")
        return value

    def validate(self, data):
        """Validate date logic."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date > end_date:
            raise serializers.ValidationError("End date must be greater than start date.")
        if start_date < timezone.now():
            raise serializers.ValidationError("Cannot reserve a car in the past.")
        return data
