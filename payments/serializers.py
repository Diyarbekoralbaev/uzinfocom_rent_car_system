from rest_framework import serializers
from .models import PaymentModel
from users.models import UserModel
import uuid
import datetime


class PaymentSerializer(serializers.ModelSerializer):
    # Fields for the “test” payment flow
    card_number = serializers.CharField(
        max_length=16,
        write_only=True,
        help_text="16-digit card number"
    )
    expiry_date = serializers.CharField(
        max_length=5,  # e.g. "12/25"
        write_only=True,
        help_text="MM/YY format"
    )
    cvv = serializers.CharField(
        max_length=3,
        write_only=True,
        help_text="3-digit card security code"
    )

    class Meta:
        model = PaymentModel
        # We'll expose only some fields from PaymentModel to the API
        fields = [
            'id',
            'user',
            'amount',
            'payment_time',
            'status',
            'transaction_id',
            'card_number',
            'expiry_date',
            'cvv',
        ]
        read_only_fields = [
            'id',
            'status',
            'transaction_id',
            'payment_time',
        ]
        extra_kwargs = {
            'user': {'required': False},  # We'll set the user from request
            'amount': {'required': True},  # Must supply amount
        }

    def validate_card_number(self, value):
        """Quick check: must be 16 digits (for test)."""
        if len(value) != 16 or not value.isdigit():
            raise serializers.ValidationError("Invalid card number. Must be 16 digits.")
        return value

    def validate_expiry_date(self, value):
        """Quick check: must be MM/YY and not expired (for test)."""
        try:
            month_str, year_str = value.split('/')
            month = int(month_str)
            year = int(year_str)
            if not (1 <= month <= 12):
                raise ValueError
            # We assume 20xx. If user typed '25', interpret as 2025:
            year += 2000
            # Check if not expired:
            now = datetime.datetime.now()
            last_day_of_month = datetime.datetime(year, month, 1, 0, 0) + datetime.timedelta(days=31)
            if now > last_day_of_month:
                raise serializers.ValidationError("Card is expired.")
        except (ValueError, IndexError):
            raise serializers.ValidationError("Expiry date must be MM/YY (e.g. 12/25).")
        return value

    def validate_cvv(self, value):
        """Quick check: must be 3 digits."""
        if len(value) != 3 or not value.isdigit():
            raise serializers.ValidationError("CVV must be 3 digits.")
        return value

    def create(self, validated_data):
        """
        1. Remove the card details so they never get stored in the DB.
        2. Mark payment as COMPLETED if everything is valid.
        3. Optionally, update user's balance or do other logic.
        """
        card_number = validated_data.pop('card_number', None)
        expiry_date = validated_data.pop('expiry_date', None)
        cvv = validated_data.pop('cvv', None)

        # We do NOT store these card fields.

        validated_data['status'] = 'COMPLETED'

        # If not provided, set the user from context (request user).
        if 'user' not in validated_data:
            request = self.context.get('request', None)
            if request and request.user.is_authenticated:
                validated_data['user'] = request.user

        # Create the payment record
        payment = PaymentModel.objects.create(**validated_data)

        user = payment.user
        user.balance += payment.amount
        user.save()

        return payment
