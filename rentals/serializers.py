from rest_framework import serializers
from .models import RentalModel, ReservationModel
from users.models import UserModel
from vehicles.models import VehicleModel, VehicleStatusChoices
from stations.models import StationModel
from django.utils import timezone

class RentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalModel
        fields = [
            'id', 'client', 'car', 'pickup_station', 'return_station',
            'start_date', 'end_date', 'total_amount', 'status',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'id': {'read_only': True},
            'client': {'read_only': True},
            'status': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'total_amount': {'read_only': True},
            'start_date': {'required': True},
            'end_date': {'required': True},
            'pickup_station': {'required': True},
            'return_station': {'required': False},
        }

    def validate(self, data):
        """
        Check date logic:
          - end_date > start_date
          - start_date >= now() (no renting in the past)
        """
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be greater than start date.")
        if data['start_date'] < timezone.now():
            raise serializers.ValidationError("Cannot rent a car in the past.")
        return data

    def validate_car(self, value):
        """Check that the car is available."""
        if value.status != VehicleStatusChoices.AVAILABLE:
            raise serializers.ValidationError("Vehicle is not available.")
        return value

    def validate_pickup_station(self, value):
        """Check that station is active."""
        if not value.is_active:
            raise serializers.ValidationError("Pickup station is not active.")
        return value

    def validate_return_station(self, value):
        """Check that station is active if specified."""
        if value and not value.is_active:
            raise serializers.ValidationError("Return station is not active.")
        return value



class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationModel
        fields = ['id', 'client', 'car', 'start_date', 'end_date', 'status', 'created_at', 'updated_at']
        extra_kwargs = {
            'id': {'read_only': True},
            'client': {'read_only': True},
            'status': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }

    def validate_client(self, value):
        if value.role != 'CL':
            raise serializers.ValidationError("Only clients can reserve vehicles.")
        client = UserModel.objects.get(id=value.id)
        if not client or not client.is_verified:
            raise serializers.ValidationError("Client not found or not verified.")
        return value

    def validate_car(self, value):
        if not value.status == VehicleStatusChoices.AVAILABLE:
            raise serializers.ValidationError("Vehicle is not available.")
        return value

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("End date must be greater than start date.")
        if data['start_date'] < timezone.now():
            raise serializers.ValidationError("Cannot reserve a car in the past.")
        return data
