from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from users.models import UserChoice
from .models import StationModel
from .serializers import StationSerializer
from .permissions import IsManager, IsAuthenticatedClientOrManager

@method_decorator(gzip_page, name='dispatch')
class StationViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing station instances.
    """
    serializer_class = StationSerializer
    permission_classes = [IsAuthenticatedClientOrManager]
    queryset = StationModel.objects.all()

    def get_queryset(self):
        """
        Override the default `get_queryset` to handle filtering based on user role.
        - Managers can see all stations.
        - Other users see only active stations, ordered by name.
        """
        user = self.request.user
        if user.role == UserChoice.MANAGER:
            return self.queryset
        return self.queryset.filter(is_active=True).order_by('name')

    def perform_create(self, serializer):
        """
        Restrict creation to managers only.
        """
        if self.request.user.role != UserChoice.MANAGER:
            raise PermissionDenied("Only managers can create stations.")
        serializer.save()

    def perform_update(self, serializer):
        """
        Restrict updates to managers only.
        """
        if self.request.user.role != UserChoice.MANAGER:
            raise PermissionDenied("Only managers can update stations.")
        serializer.save()

    def perform_destroy(self, instance):
        """
        Restrict deletion to managers only.
        """
        if self.request.user.role != UserChoice.MANAGER:
            raise PermissionDenied("Only managers can delete stations.")
        instance.delete()

    @swagger_auto_schema(
        operation_id="activate_station",
        operation_summary="Activate a station",
        operation_description="Allows managers to activate a station.",
        responses={
            200: openapi.Response(
                description="Station successfully activated.",
                schema=StationSerializer()
            ),
            403: "Forbidden",
            400: "Bad Request"
        }
    )
    @action(detail=True, methods=['post'], url_path='activate', permission_classes=[IsManager])
    def activate(self, request, pk=None):
        """
        Custom action to activate a station. Accessible only by managers.
        """
        station = self.get_object()
        if station.is_active:
            return Response({'detail': 'Station is already active.'}, status=status.HTTP_400_BAD_REQUEST)
        station.is_active = True
        station.save()
        serializer = self.get_serializer(station)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="deactivate_station",
        operation_summary="Deactivate a station",
        operation_description="Allows managers to deactivate a station.",
        responses={
            200: openapi.Response(
                description="Station successfully deactivated.",
                schema=StationSerializer()
            ),
            403: "Forbidden",
            400: "Bad Request"
        }
    )
    @action(detail=True, methods=['post'], url_path='deactivate', permission_classes=[IsManager])
    def deactivate(self, request, pk=None):
        """
        Custom action to deactivate a station. Accessible only by managers.
        """
        station = self.get_object()
        if not station.is_active:
            return Response({'detail': 'Station is already inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        station.is_active = False
        station.save()
        serializer = self.get_serializer(station)
        return Response(serializer.data, status=status.HTTP_200_OK)
