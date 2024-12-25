from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator

from users.models import UserChoice
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F
from .models import VehicleModel, VehicleStatusChoices
from .serializers import VehicleSerializer, VehicleAvailabilitySerializer
from drf_yasg import openapi
from .permissions import IsManager, IsAuthenticatedClientOrManager

@method_decorator(gzip_page, name='dispatch')
class VehicleViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing vehicle instances.
    """
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticatedClientOrManager]
    queryset = VehicleModel.objects.all()

    def get_queryset(self):
        """
        Override the default `get_queryset` to handle filtering based on user role.
        """
        user = self.request.user
        if user.role == UserChoice.CLIENT:
            return self.queryset.filter(status=VehicleStatusChoices.AVAILABLE)
        elif user.role == UserChoice.MANAGER:
            return self.queryset
        return VehicleModel.objects.none()

    def perform_create(self, serializer):
        """
        Restrict creation to managers only.
        """
        if self.request.user.role != 'MANAGER':
            raise PermissionDenied("You do not have permission to create a vehicle.")
        serializer.save()

    def perform_update(self, serializer):
        """
        Restrict updates to managers only.
        """
        if self.request.user.role != 'MANAGER':
            raise PermissionDenied("You do not have permission to update a vehicle.")
        serializer.save()

    def perform_destroy(self, instance):
        """
        Restrict deletion to managers only.
        """
        if self.request.user.role != 'MANAGER':
            raise PermissionDenied("You do not have permission to delete a vehicle.")
        instance.delete()

    @swagger_auto_schema(
        operation_id="set_vehicle_status",
        operation_summary="Set vehicle availability",
        operation_description="Set the availability of a vehicle",
        request_body=VehicleAvailabilitySerializer,
        responses={
            200: VehicleAvailabilitySerializer(),
            400: 'Bad Request',
            403: 'Forbidden'
        }
    )
    @action(detail=True, methods=['post'], url_path='set-status', permission_classes=[IsManager])
    def set_status(self, request, pk=None):
        """
        Custom action to set the status of a vehicle. Accessible only by managers.
        """
        vehicle = self.get_object()
        serializer = VehicleAvailabilitySerializer(vehicle, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)