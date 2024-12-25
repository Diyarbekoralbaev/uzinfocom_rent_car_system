from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator

from users.models import UserChoice
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F
from .models import VehicleModel
from .serializers import VehicleSerializer, VehicleAvailabilitySerializer
from drf_yasg import openapi


@method_decorator(gzip_page, name='dispatch')
class VehicleViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing vehicle instances.
    """
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    queryset = VehicleModel.objects.all()

    def get_queryset(self):
        """
        Overriding the default `get_queryset` to handle filtering based on user role.
        """
        if self.request.user.role == UserChoice.CLIENT and self.request.user.is_authenticated:
            return VehicleModel.objects.filter(is_available=True)
        elif self.request.user.role == UserChoice.MANAGER and self.request.user.is_authenticated:
            return VehicleModel.objects.all()
        return VehicleModel.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().create(request, *args, **kwargs)
        return Response({"error": "You do not have permission to create a vehicle"}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().update(request, *args, **kwargs)
        return Response({"error": "You do not have permission to update a vehicle"}, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().partial_update(request, *args, **kwargs)
        return Response({"error": "You do not have permission to update a vehicle"}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().destroy(request, *args, **kwargs)
        return Response({"error": "You do not have permission to delete a vehicle"}, status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        operation_id="Set vehicle availability",
        operation_summary="Set vehicle availability",
        operation_description="Set the availability of a vehicle",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Vehicle status',
                                         enum=['AVAILABLE', 'RENTED', 'MAINTENANCE'])
            }
        ),
        responses={200: VehicleAvailabilitySerializer()}
    )
    @action(detail=True, methods=['post'], url_path='set-status', permission_classes=[IsAuthenticated])
    def set_status(self, request, pk=None):
        user = request.user
        if user.role == UserChoice.MANAGER:
            vehicle = self.get_object()
            serializer = VehicleAvailabilitySerializer(vehicle, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "You do not have permission to set availability of a vehicle"}, status=status.HTTP_403_FORBIDDEN)