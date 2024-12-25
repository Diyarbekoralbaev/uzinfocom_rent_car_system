from rest_framework import serializers
from .models import StationModel

class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationModel
        fields = ['id', 'name', 'latitude', 'longitude', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': True},
            'latitude': {'required': True},
            'longitude': {'required': True},
            'is_active': {'required': False},
        }

    def validate_name(self, value):
        if self.instance:
            # For updates, exclude the current instance from uniqueness check
            if StationModel.objects.filter(name=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError('This station name is already taken.')
        else:
            if StationModel.objects.filter(name=value).exists():
                raise serializers.ValidationError('This station name is already taken.')
        return value
