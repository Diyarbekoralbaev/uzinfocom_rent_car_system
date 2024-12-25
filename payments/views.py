from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import PaymentModel
from .serializers import PaymentSerializer
from .utils import send_payment_email
from users.models import UserChoice

class PaymentViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for handling test payments.
    """
    serializer_class = PaymentSerializer
    queryset = PaymentModel.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        - If user is Manager, they can see all payments.
        - If user is Client, only see their own.
        """
        user = self.request.user
        if user.role == UserChoice.MANAGER:
            return PaymentModel.objects.all().order_by('-payment_time')
        return PaymentModel.objects.filter(user=user).order_by('-payment_time')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Override create to do atomic DB writes.
        The PaymentSerializer handles the card details in memory only.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        send_payment_email(payment.user.email, payment.amount)
        return Response(self.get_serializer(payment).data, status=status.HTTP_201_CREATED)
