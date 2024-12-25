from datetime import datetime

from django.db import transaction
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
from .models import RentalModel, ReservationModel, RentalStatusChoices, ReservationStatusChoices
from users.models import UserChoice, UserModel
from .serializers import RentalSerializer, ReservationSerializer
from .utils import is_near_station
from django.db.models import F

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
            return RentalModel.objects.select_related('car').filter(client=self.request.user)
        elif self.request.user.is_authenticated and self.request.user.role == UserChoice.MANAGER:
            return RentalModel.objects.select_related('car', 'client').prefetch_related('pickup_station', 'return_station')
        return RentalModel.objects.none()

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            user = UserModel.objects.select_for_update().get(id=request.user.id)
            vehicle = VehicleModel.objects.select_for_update().get(id=request.data['car'])
            if RentalModel.objects.filter(client=user, status='ACTIVE').exists():
                return Response({"error": "You already have an active rental"},
                                status=status.HTTP_400_BAD_REQUEST)
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            if ReservationModel.objects.filter(car=request.data['car'], start_date__lte=end_date, end_date__gte=start_date, status='CONFIRMED').exists():
                return Response({"error": "This car is already reserved in this time period. Please choose another car or time period."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                price = vehicle.daily_price
                start_date = request.data['start_date']
                end_date = request.data['end_date']
                total_amount = price * (end_date - start_date).days
                if user.balance < total_amount:
                    return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)
                user.balance = F('balance') - total_amount
                user.save()
                # Create the rental
                data = request.data.copy()
                data['client'] = user.id
                data['status'] = RentalStatusChoices.PENDING
                data['total_amount'] = total_amount

                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                rental = serializer.save()

                return Response(RentalSerializer(rental).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            user = UserModel.objects.select_for_update().get(id=request.user.id)
            rental = self.get_object()
            if user.role == UserChoice.CLIENT:
                if request.data.get('status') == RentalStatusChoices.CANCELLED:
                    if rental.status == RentalStatusChoices.PENDING:
                        user.balance += rental.total_amount
                        user.save()
                    if rental.status == RentalStatusChoices.ACTIVE:
                        return Response({"error": "You cannot cancel an active rental. Please return the car to the station and set status to completed."}, status=status.HTTP_400_BAD_REQUEST)
                    return super().update(request, *args, **kwargs)
                # Handle date updates
                if 'start_date' in request.data or 'end_date' in request.data:
                    start_date = request.data.get('start_date', rental.start_date)
                    end_date = request.data.get('end_date', rental.end_date)

                    try:
                        # Parse dates if they are strings
                        if isinstance(start_date, str):
                            start_date = datetime.fromisoformat(start_date)
                        if isinstance(end_date, str):
                            end_date = datetime.fromisoformat(end_date)

                        # Validate date logic
                        if start_date >= end_date:
                            return Response({"error": "Start date must be before end date"},
                                            status=status.HTTP_400_BAD_REQUEST)

                        # Calculate new total based on updated dates
                        new_total_amount = rental.car.daily_price * (end_date - start_date).days

                        # Calculate the difference from the already charged amount
                        amount_difference = new_total_amount - rental.total_amount

                        # Check and update user balance
                        if amount_difference > 0:  # New total is higher, charge the user
                            if user.balance < amount_difference:
                                return Response({"error": "Insufficient balance to update rental"},
                                                status=status.HTTP_400_BAD_REQUEST)
                            user.balance -= amount_difference
                        elif amount_difference < 0:  # New total is lower, refund the user
                            user.balance += abs(amount_difference)

                        # Save the updated balance and proceed
                        user.save()
                        request.data['total_amount'] = new_total_amount

                    except ValueError:
                        return Response({"error": "Invalid date format provided"}, status=status.HTTP_400_BAD_REQUEST)
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
        with transaction.atomic():
            user = request.user
            if user.role == UserChoice.MANAGER:
                rental = self.get_object()
                new_status = request.data.get('status')

                if not rental.can_transition_to(new_status):
                    return Response({"error": f"Cannot transition from {rental.status} to {new_status}"},
                                    status=status.HTTP_400_BAD_REQUEST)

                if new_status not in [RentalStatusChoices.ACTIVE, RentalStatusChoices.COMPLETED,
                                      RentalStatusChoices.CANCELLED]:
                    return Response({"error": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

                if new_status == RentalStatusChoices.CANCELLED and rental.status == RentalStatusChoices.ACTIVE:
                    return Response({"error": "You cannot cancel an active rental. Please return the car to the station and set status to completed."}, status=status.HTTP_400_BAD_REQUEST)

                if new_status == RentalStatusChoices.ACTIVE:
                    # check for exiting reservation or rental in the same time
                    if ReservationModel.objects.filter(car=rental.car, start_date__lte=rental.end_date, end_date__gte=rental.start_date, status='CONFIRMED').exists():
                        return Response({"error": "This car is already reserved in this time period. Cancel the reservation first."}, status=status.HTTP_400_BAD_REQUEST)
                    pending_reservations = ReservationModel.objects.filter(car=rental.car, start_date__lte=rental.end_date, end_date__gte=rental.start_date, status='PENDING')
                    if pending_reservations.exists():
                        for reservation in pending_reservations:
                            reservation.status = ReservationStatusChoices.CANCELLED
                            reservation.save()
                elif new_status == RentalStatusChoices.COMPLETED:
                    if not rental.return_station:
                        return Response({"error": "Please set return station before completing the rental"}, status=status.HTTP_400_BAD_REQUEST)

                rental.status = new_status
                rental.save()

                vehicle = rental.car
                if rental.status == RentalStatusChoices.ACTIVE:
                    vehicle.status = VehicleStatusChoices.RENTED
                if rental.status == RentalStatusChoices.CANCELLED:
                    client = rental.client
                    client.balance += rental.total_amount
                    client.save()
                    vehicle.status = VehicleStatusChoices.AVAILABLE
                elif rental.status == RentalStatusChoices.COMPLETED:
                    vehicle.status = VehicleStatusChoices.AVAILABLE
                vehicle.save()

                return Response({"status": rental.status}, status=status.HTTP_200_OK)

            return Response({"error": "You do not have permission to set status of a rental"},
                            status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        methods=['post'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'return_station': openapi.Schema(type=openapi.TYPE_INTEGER),
                'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
            }
        ),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT)}
    )
    @action(detail=False, methods=['post'], url_path='return-car-to-station', permission_classes=[IsAuthenticated])
    def return_car_to_station(self, request):
        user = request.user
        if user.role == UserChoice.CLIENT:
            rental = RentalModel.objects.get(client=user, status='ACTIVE')
            station = StationModel.objects.filter(id=request.data['return_station']).first()
            if not station:
                return Response({"error": "Station not found"}, status=status.HTTP_400_BAD_REQUEST)

            user_lat = request.data.get('latitude')
            user_lon = request.data.get('longitude')

            if not is_near_station(user_lat, user_lon, station.latitude, station.longitude):
                return Response({"error": "You are not near the station"}, status=status.HTTP_400_BAD_REQUEST)

            if rental:
                rental.status = 'COMPLETED'
                rental.return_station = station
                rental.save()
                vehicle = rental.car
                vehicle.status = VehicleStatusChoices.AVAILABLE
                vehicle.current_station = rental.return_station
                vehicle.save()
                return Response({"message": "Car returned to station successfully"}, status=status.HTTP_200_OK)
            return Response({"error": "No active rental found"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "You do not have permission to return a car to station"},
                        status=status.HTTP_403_FORBIDDEN)

@method_decorator(gzip_page, name='dispatch')
class ReservationViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing reservation instances.
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]
    queryset = ReservationModel.objects.all()
    http_method_names = ['get', 'post']

    def get_queryset(self):
        """
        Overriding the default `get_queryset` to handle filtering based on user role.
        """
        if self.request.user.is_authenticated and self.request.user.role == UserChoice.CLIENT:
            return ReservationModel.objects.filter(client=self.request.user)
        elif self.request.user.is_authenticated and self.request.user.role == UserChoice.MANAGER:
            return ReservationModel.objects.all()
        return ReservationModel.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        vehicle_id = request.data['car']
        start_date = request.data['start_date']
        end_date = request.data['end_date']
        with transaction.atomic():
            vehicle = VehicleModel.objects.select_for_update().get(id=vehicle_id)
            if ReservationModel.objects.filter(client=user, car=vehicle, status=ReservationStatusChoices.CONFIRMED/ReservationStatusChoices.PENDING).exists(): # noqa
                return Response({"error": "You already have a reservation for this car. Please wait for the manager to confirm or cancel it."}, status=status.HTTP_400_BAD_REQUEST)
            # check for exiting reservation or rental in the same time
            if ReservationModel.objects.filter(
                    client=user,
                    car=vehicle,
                    status__in=[ReservationStatusChoices.PENDING, ReservationStatusChoices.CONFIRMED],
                    start_date__lte=end_date,
                    end_date__gte=start_date
            ).exists():
                return Response(
                    {"error": "You already have an overlapping reservation for this car."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if RentalModel.objects.filter(car=vehicle, start_date__lte=end_date, end_date__gte=start_date, status='ACTIVE').exists():
                return Response({"error": "This car is already rented in this time period. Please choose another car or time period."}, status=status.HTTP_400_BAD_REQUEST)
            # no need charge for reservation now. charge will be done when rental is created
            request.data['client'] = user.id
            request.data['status'] = ReservationStatusChoices.PENDING
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Update not allowed for reservations
        """
        return Response({"error": "Update not allowed for reservations"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        """
        Partial update not allowed for reservations
        """
        return Response({"error": "Partial update not allowed for reservations"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        """
        Delete not allowed for reservations
        """
        return Response({"error": "Delete not allowed for reservations"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

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
            reservation = self.get_object()
            serializer = ReservationSerializer(reservation, data=request.data, partial=True)
            if serializer.is_valid():
                reservation = serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "You do not have permission to set status of a reservation"}, status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        methods=['post'],
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT)}
    )
    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        user = request.user
        reservation = self.get_object()
        if user.role == UserChoice.CLIENT:
            if reservation.status == ReservationStatusChoices.PENDING or reservation.status == ReservationStatusChoices.CONFIRMED:
                reservation.status = ReservationStatusChoices.CANCELLED
                reservation.save()
                return Response({"message": "Reservation cancelled successfully"}, status=status.HTTP_200_OK)
            return Response({"error": "You cannot cancel a reservation that is already cancelled"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Manager cannot cancel a reservation from a client. Please use set-status endpoint."}, status=status.HTTP_403_FORBIDDEN)