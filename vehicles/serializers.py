from rest_framework import serializers
from .models import VehicleModel

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = '__all__'
        extra_kwargs = {
            'id': {'read_only': True},
            'current_station': {'required': False},
        }

    def validate(self, data):
        data = super().validate(data)
        return data

    def create(self, validated_data):
        vehicle = VehicleModel.objects.create(**validated_data)
        return vehicle


class VehicleAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = ('id', 'status')
        extra_kwargs = {
            'id': {'read_only': True},
            'status': {'required': True},
        }

    def validate(self, data):
        data = super().validate(data)
        return data