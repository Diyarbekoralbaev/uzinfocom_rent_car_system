import datetime

from rest_framework import serializers

from .models import PaymentModel, PaymentStatusChoices


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
        # Explicitly defining fields for security and clarity
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
            'user': {'required': False},  # Set from request context
            'amount': {'required': True},
        }

    def validate_card_number(self, value):
        """Validate that the card number is exactly 16 digits."""
        if len(value) != 16 or not value.isdigit():
            raise serializers.ValidationError("Invalid card number. Must be 16 digits.")
        return value

    def validate_expiry_date(self, value):
        """Validate expiry date is in MM/YY format and not expired."""
        try:
            month_str, year_str = value.split('/')
            month = int(month_str)
            year = int(year_str)
            if not (1 <= month <= 12):
                raise ValueError
            # Assume 20xx for year
            year += 2000
            # Check if not expired
            now = datetime.datetime.now()
            last_day_of_month = datetime.datetime(year, month, 1) + datetime.timedelta(days=31)
            if now > last_day_of_month:
                raise serializers.ValidationError("Card is expired.")
        except (ValueError, IndexError):
            raise serializers.ValidationError("Expiry date must be MM/YY (e.g. 12/25).")
        return value

    def validate_cvv(self, value):
        """Validate that CVV is exactly 3 digits."""
        if len(value) != 3 or not value.isdigit():
            raise serializers.ValidationError("CVV must be 3 digits.")
        return value

    def create(self, validated_data):
        """
        1. Remove card details to ensure they are not stored.
        2. Mark payment as COMPLETED if valid.
        3. Update user's balance.
        """
        # Remove sensitive card information
        card_number = validated_data.pop('card_number', None)
        expiry_date = validated_data.pop('expiry_date', None)
        cvv = validated_data.pop('cvv', None)

        # Ensure card details are not stored
        # Note: In a real-world scenario, integrate with a payment gateway instead

        # Set status to COMPLETED
        validated_data['status'] = PaymentStatusChoices.COMPLETED

        # Set user from context if not provided
        if 'user' not in validated_data:
            request = self.context.get('request', None)
            if request and request.user.is_authenticated:
                validated_data['user'] = request.user
            else:
                raise serializers.ValidationError("User must be authenticated or provided.")

        # Create the payment record
        payment = PaymentModel.objects.create(**validated_data)

        # Update user's balance
        user = payment.user
        user.balance += payment.amount
        user.save()

        return payment
