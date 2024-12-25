from django.template.context_processors import request
from django.views.decorators.gzip import gzip_page
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from rest_framework.response import Response

from stations.models import StationModel
from vehicles.models import VehicleModel, VehicleStatusChoices
from .models import RentalModel, ReservationModel, RentalStatusChoices
from users.models import UserChoice
from .serializers import RentalSerializer, ReservationSerializer


@method_decorator(gzip_page, name='dispatch')
class RentalViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing rental instances.
    """
    serializer_class = RentalSerializer
    permission_classes = [IsAuthenticated]
    queryset = RentalModel.objects.all()

    def get_queryset(self):
        """
        Overriding the default `get_queryset` to handle filtering based on user role.
        """
        if self.request.user.is_authenticated and self.request.user.role == UserChoice.CLIENT:
            return RentalModel.objects.filter(client=self.request.user)
        elif self.request.user.is_authenticated and self.request.user.role == UserChoice.MANAGER:
            return RentalModel.objects.all()
        return RentalModel.objects.none()

    def create(self, request, *args, **kwargs):
        rentals = RentalModel.objects.filter(client=request.user, status='ACTIVE')
        if rentals.exists():
            return Response({"error": "You already have an active rental"}, status=status.HTTP_400_BAD_REQUEST)
        reservations = ReservationModel.objects.filter(client=request.user, status='CONFIRMED')
        if reservations.exists():
            return Response({"error": "You already have an active reservation"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = request.user
            vehicle = VehicleModel.objects.get(id=request.data['car'])
            price = vehicle.daily_price
            start_date = request.data['start_date']
            end_date = request.data['end_date']
            total_amount = price * (end_date - start_date).days
            if user.balance < total_amount:
                return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)
            user.balance -= total_amount
            user.save()
            request.data['total_amount'] = total_amount
            request.data['client'] = user.id
            request.data['status'] = 'PENDING'
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.CLIENT:
            return super().update(request, *args, **kwargs)
        return Response({"error": "You do not have permission to update a rental"}, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.CLIENT:
            return super().partial_update(request, *args, **kwargs)
        return Response({"error": "You do not have permission to update a rental"}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.CLIENT:
            return super().destroy(request, *args, **kwargs)
        return Response({"error": "You do not have permission to delete a rental"}, status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        methods=['post'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT)}
    )
    @action(detail=True, methods=['post'], url_path='set-status', permission_classes=[IsAuthenticated])
    def set_status(self, request, pk=None):
        user = request.user
        if user.role == UserChoice.MANAGER:
            rental = self.get_object()
            serializer = RentalSerializer(rental, data=request.data, partial=True)
            if serializer.is_valid():
                rental = serializer.save()
                vehicle = rental.car
                if rental.status == RentalStatusChoices.ACTIVE:
                    vehicle.status = VehicleStatusChoices.RENTED
                elif rental.status == RentalStatusChoices.COMPLETED or rental.status == RentalStatusChoices.CANCELLED:
                    vehicle.status = VehicleStatusChoices.AVAILABLE
                vehicle.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "You do not have permission to set status of a rental"}, status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        methods=['get'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'return_station': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT)}
    )
    @action(detail=False, methods=['get'], url_path='return-car-to-station', permission_classes=[IsAuthenticated])
    def return_car_to_station(self, request):
        user = request.user
        if user.role == UserChoice.CLIENT:
            rental = RentalModel.objects.get(client=user, status='ACTIVE')
            if not StationModel.objects.filter(id=request.data['return_station']).exists():
                return Response({"error": "Station not found"}, status=status.HTTP_400_BAD_REQUEST)
            if rental:
                rental.status = 'COMPLETED'
                rental.return_station = request.data['return_station']
                rental.save()
                vehicle = rental.car
                vehicle.status = VehicleStatusChoices.AVAILABLE
                vehicle.current_station = rental.return_station
                vehicle.save()
                return Response({"message": "Car returned to station successfully"}, status=status.HTTP_200_OK)
            return Response({"error": "No active rental found"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "You do not have permission to return a car to station"}, status=status.HTTP_403_FORBIDDEN)
