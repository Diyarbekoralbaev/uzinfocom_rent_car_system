from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import UserModel, UserChoice
from rest_framework_simplejwt.tokens import RefreshToken

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('id', 'first_name', 'last_name', 'username', 'password', 'email', 'phone', 'balance', 'role', 'is_verified')
        extra_kwargs = {
            'id': {'read_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'username': {'required': True},
            'password': {'write_only': True},
            'phone': {'required': True},
            'balance': {'read_only': True},
            'email': {'required': False},
            'role': {'required': False},
            'is_verified': {'read_only': True},
        }

    def validate_username(self, value):
        if UserModel.objects.filter(username=value, is_verified=True).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate(self, data):
        data = super().validate(data)
        return data

    def create(self, validated_data):
        user = UserModel.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=500, write_only=True)

    def validate(self, data):
        username = data.get('username', None)
        password = data.get('password', None)
        if username is None:
            raise serializers.ValidationError('A username is required to log in.')
        if password is None:
            raise serializers.ValidationError('A password is required to log in.')
        user = authenticate(username=username, password=password)
        if user is None:
            raise serializers.ValidationError('A user with this username and password was not found.')
        if not user.is_verified:
            raise serializers.ValidationError('This user is not verified yet. Please verify your email or phone number.')
        refresh = RefreshToken.for_user(user)
        return {
            'username': user.username,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class VerifySerializer(serializers.Serializer):
    verification_id = serializers.CharField(max_length=36)
    code = serializers.CharField(max_length=10)

    def validate(self, data):
        uuid = data.get('verification_id', None)
        code = data.get('code', None)
        if uuid is None:
            raise serializers.ValidationError('A UUID is required to verify the user.')
        if code is None:
            raise serializers.ValidationError('A code is required to verify the user.')
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=500)
    new_password = serializers.CharField(max_length=500)

    def validate(self, data):
        old_password = data.get('old_password', None)
        new_password = data.get('new_password', None)
        if old_password is None:
            raise serializers.ValidationError('The old password is required.')
        if new_password is None:
            raise serializers.ValidationError('The new password is required.')
        if old_password == new_password:
            raise serializers.ValidationError('The new password must be different from the old password.')
        return data

class ResetPasswordSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(max_length=150)


class ResetPasswordConfirmSerializer(serializers.Serializer):
    verification_id = serializers.CharField(max_length=36)
    code = serializers.CharField(max_length=10)
    new_password = serializers.CharField(max_length=500)

    def validate(self, data):
        uuid = data.get('verification_id', None)
        code = data.get('code', None)
        new_password = data.get('new_password', None)
        if uuid is None:
            raise serializers.ValidationError('A UUID is required to reset the password.')
        if code is None:
            raise serializers.ValidationError('A code is required to reset the password.')
        if new_password is None:
            raise serializers.ValidationError('A new password is required to reset the password.')
        return data


class TopUpSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        user_id = data.get('user_id', None)
        amount = data.get('amount', None)
        if user_id is None:
            raise serializers.ValidationError('A user ID is required to top up the balance.')
        if amount is None:
            raise serializers.ValidationError('An amount is required to top up the balance.')
        if amount <= 0:
            raise serializers.ValidationError('The amount must be greater than 0.')
        if not UserModel.objects.filter(id=user_id).exists():
            raise serializers.ValidationError('A user with this ID was not found.')
        if UserModel.objects.get(id=user_id).role == UserChoice.MANAGER:
            raise serializers.ValidationError('Managers cannot top up their balance.')
        return data