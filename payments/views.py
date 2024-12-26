from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from users.models import UserChoice
from .models import PaymentModel
from common.permissions import IsClient
from .serializers import PaymentSerializer
from .utils import send_payment_email


@method_decorator(gzip_page, name='dispatch')
class PaymentViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for handling test payments.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsClient]
    queryset = PaymentModel.objects.select_related('user').all()

    def get_queryset(self):
        """
        - Managers can see all payments.
        - Clients can only see their own payments.
        """
        user = self.request.user
        if user.role == UserChoice.MANAGER:
            return self.queryset.order_by('-payment_time')
        return self.queryset.filter(user=user).order_by('-payment_time')

    def perform_create(self, serializer):
        """
        Handle payment creation within an atomic transaction.
        """
        with transaction.atomic():
            payment = serializer.save()
            send_payment_email(payment.id)

    @swagger_auto_schema(
        operation_id="create_payment",
        operation_summary="Create a payment",
        operation_description="Endpoint to create a new payment.",
        request_body=PaymentSerializer,
        responses={
            201: PaymentSerializer(),
            400: "Bad Request",
            403: "Forbidden"
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Override create to handle atomic transactions and email sending.
        """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id="list_payments",
        operation_summary="List payments",
        operation_description="List all payments for managers or own payments for clients.",
        responses={
            200: PaymentSerializer(many=True),
            403: "Forbidden"
        }
    )
    def list(self, request, *args, **kwargs):
        """
        Override list to provide custom Swagger documentation if needed.
        """
        return super().list(request, *args, **kwargs)
