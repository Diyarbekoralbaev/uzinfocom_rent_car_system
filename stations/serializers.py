from rest_framework import serializers
from .models import StationModel

class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationModel
        fields = ('id', 'name', 'latitude', 'longitude', 'is_active','created_at', 'updated_at')
        extra_kwargs = {
            'id': {'read_only': True},
            'name': {'required': True},
            'latitude': {'required': True},
            'longitude': {'required': True},
            'is_active': {'required': False},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }

    def validate_name(self, value):
        if StationModel.objects.filter(name=value).exists():
            raise serializers.ValidationError('This station name is already taken.')
        return value

    def validate(self, data):
        data = super().validate(data)
        return data

    def create(self, validated_data):
        station = StationModel.objects.create(**validated_data)
        return station