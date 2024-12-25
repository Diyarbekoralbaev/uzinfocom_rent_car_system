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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        1. Lock user & vehicle rows.
        2. Check for active rental, overlapping reservations, etc.
        3. Deduct user balance.
        4. Create rental.
        """
        user = UserModel.objects.select_for_update().get(id=request.user.id)
        vehicle = VehicleModel.objects.select_for_update().get(id=request.data['car'])

        # Ensure client does not have an active rental
        if RentalModel.objects.filter(client=user, status=RentalStatusChoices.ACTIVE).exists():
            return Response({"error": "You already have an active rental."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = datetime.fromisoformat(request.data.get('start_date'))
        end_date = datetime.fromisoformat(request.data.get('end_date'))

        # Check for confirmed reservation overlap
        if ReservationModel.objects.filter(
            car=vehicle,
            start_date__lte=end_date,
            end_date__gte=start_date,
            status=ReservationStatusChoices.CONFIRMED
        ).exists():
            return Response({
                "error": "This car is reserved for that period. Please choose another car or time."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total amount (simple daily rate * day difference)
        daily_price = vehicle.daily_price
        day_count = (end_date.date() - start_date.date()).days
        if day_count < 1:
            day_count = 1  # Minimum 1 day billing if your business logic requires
        total_amount = daily_price * day_count

        # Check user balance
        if user.balance < total_amount:
            return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct balance
        user.balance = F('balance') - total_amount
        user.save()

        # Create the rental record
        data = request.data.copy()
        data['client'] = user.id
        data['status'] = RentalStatusChoices.PENDING
        data['total_amount'] = total_amount

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        rental = serializer.save()

        return Response(RentalSerializer(rental).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Handle full updates (PUT). Typically, you might let clients:
          - Cancel a pending rental
          - Extend or adjust dates (if still pending or not started)
        Managers: could also forcibly update fields if needed
        """
        user = UserModel.objects.select_for_update().get(id=request.user.id)
        # Lock the rental row as well
        rental = RentalModel.objects.select_for_update().get(pk=kwargs['pk'])

        # ----- Check Permissions by Role -----
        if user.role == UserChoice.CLIENT:
            # Example: allow client to cancel if status = PENDING
            new_status = request.data.get('status')
            new_start_date = request.data.get('start_date')
            new_end_date = request.data.get('end_date')

            # If client wants to cancel
            if new_status == RentalStatusChoices.CANCELLED:
                if rental.status == RentalStatusChoices.PENDING:
                    # Refund
                    user.balance = F('balance') + rental.total_amount
                    user.save()
                    rental.status = RentalStatusChoices.CANCELLED
                    rental.save()
                    return Response(RentalSerializer(rental).data, status=status.HTTP_200_OK)
                elif rental.status == RentalStatusChoices.ACTIVE:
                    return Response({
                        "error": "Cannot cancel an active rental. Return the car first."
                    }, status=status.HTTP_400_BAD_REQUEST)
                # If already cancelled/completed, do nothing
                return Response({
                    "error": f"Cannot cancel a rental in {rental.status} state."
                }, status=status.HTTP_400_BAD_REQUEST)

            # If client wants to update start_date or end_date
            if new_start_date or new_end_date:
                # Must parse them if they exist
                start_date = rental.start_date
                end_date = rental.end_date

                if new_start_date:
                    try:
                        start_date = datetime.fromisoformat(new_start_date)
                    except ValueError:
                        return Response({"error": "Invalid start_date format."}, status=status.HTTP_400_BAD_REQUEST)
                if new_end_date:
                    try:
                        end_date = datetime.fromisoformat(new_end_date)
                    except ValueError:
                        return Response({"error": "Invalid end_date format."}, status=status.HTTP_400_BAD_REQUEST)

                # Validate new date logic
                if start_date >= end_date:
                    return Response({"error": "start_date must be before end_date."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Also check for overlap if the new date range is beyond original
                if ReservationModel.objects.filter(
                    car=rental.car,
                    start_date__lte=end_date,
                    end_date__gte=start_date,
                    status=ReservationStatusChoices.CONFIRMED
                ).exists():
                    return Response({"error": "This new date range conflicts with a confirmed reservation."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Calculate new total
                daily_price = rental.car.daily_price
                day_count = (end_date.date() - start_date.date()).days
                if day_count < 1:
                    day_count = 1
                new_total_amount = daily_price * day_count

                # Difference from old total
                difference = new_total_amount - rental.total_amount
                if difference > 0:
                    # Need to charge more
                    if user.balance < difference:
                        return Response({"error": "Insufficient balance to extend rental."},
                                        status=status.HTTP_400_BAD_REQUEST)
                    user.balance = F('balance') - difference
                    user.save()
                elif difference < 0:
                    # Refund the client for the difference
                    user.balance = F('balance') + abs(difference)
                    user.save()

                # Update rental object
                rental.start_date = start_date
                rental.end_date = end_date
                rental.total_amount = new_total_amount
                rental.save()

                return Response(RentalSerializer(rental).data, status=status.HTTP_200_OK)

            # If the client wants to do a PUT that changes something else (e.g. pickup_station)
            # you could handle that or just call super().update().
            return super().update(request, *args, **kwargs)

        elif user.role == UserChoice.MANAGER:
            """
            Example: Manager can forcibly update the rental if needed.
            You could replicate some or all logic from above,
            or simply call super().update().
            """
            return super().update(request, *args, **kwargs)

        # If neither client nor manager
        return Response({"error": "You do not have permission to update this rental."},
                        status=status.HTTP_403_FORBIDDEN)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """
        Handle partial updates (PATCH). Could be similar logic to update(),
        but let's let it call super() after we do any checks.
        """
        user = UserModel.objects.select_for_update().get(id=request.user.id)
        rental = RentalModel.objects.select_for_update().get(pk=kwargs['pk'])

        # For simplicity, let's say only clients & managers can do partial_update
        if user.role not in [UserChoice.CLIENT, UserChoice.MANAGER]:
            return Response({"error": "You do not have permission to update this rental."},
                            status=status.HTTP_403_FORBIDDEN)

        # Optionally, replicate date checks or allow partial fields
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if user.role == UserChoice.CLIENT:
            # Possibly you only allow deleting if it's still PENDING, etc.
            rental = self.get_object()
            if rental.status != RentalStatusChoices.PENDING:
                return Response({"error": "You can only delete rentals that are pending."},
                                status=status.HTTP_400_BAD_REQUEST)
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
        """
        Manager can forcibly set rental status if allowed transitions.
        """
        with transaction.atomic():
            user = request.user
            if user.role != UserChoice.MANAGER:
                return Response({"error": "You do not have permission to set status of a rental"},
                                status=status.HTTP_403_FORBIDDEN)

            rental = RentalModel.objects.select_for_update().get(pk=pk)
            new_status = request.data.get('status')

            if not rental.can_transition_to(new_status):
                return Response({
                    "error": f"Cannot transition from {rental.status} to {new_status}"
                }, status=status.HTTP_400_BAD_REQUEST)

            if new_status == RentalStatusChoices.CANCELLED and rental.status == RentalStatusChoices.ACTIVE:
                return Response({
                    "error": "Cannot cancel an active rental. Return the car or complete it first."
                }, status=status.HTTP_400_BAD_REQUEST)

            if new_status == RentalStatusChoices.ACTIVE:
                # check for overlapping reservations
                if ReservationModel.objects.filter(
                    car=rental.car,
                    start_date__lte=rental.end_date,
                    end_date__gte=rental.start_date,
                    status=ReservationStatusChoices.CONFIRMED
                ).exists():
                    return Response({
                        "error": "This car is already reserved in this time period. Cancel the reservation first."
                    }, status=status.HTTP_400_BAD_REQUEST)

            if new_status == RentalStatusChoices.COMPLETED:
                if not rental.return_station:
                    return Response({"error": "Set return_station before completing the rental."},
                                    status=status.HTTP_400_BAD_REQUEST)

            rental.status = new_status
            rental.save()

            # Update vehicle status
            vehicle = rental.car
            if new_status == RentalStatusChoices.ACTIVE:
                vehicle.status = VehicleStatusChoices.RENTED
            elif new_status == RentalStatusChoices.CANCELLED:
                # Refund the user
                client = rental.client
                client.balance = F('balance') + rental.total_amount
                client.save()
                vehicle.status = VehicleStatusChoices.AVAILABLE
            elif new_status == RentalStatusChoices.COMPLETED:
                vehicle.status = VehicleStatusChoices.AVAILABLE
            vehicle.save()

            return Response({"status": rental.status}, status=status.HTTP_200_OK)

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
        """
        Client returns the car to a station, verifying they are physically near the station.
        """
        user = request.user
        if user.role != UserChoice.CLIENT:
            return Response({"error": "You do not have permission to return a car."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            rental = RentalModel.objects.get(client=user, status=RentalStatusChoices.ACTIVE)
        except RentalModel.DoesNotExist:
            return Response({"error": "No active rental found for this user."}, status=status.HTTP_400_BAD_REQUEST)

        station_id = request.data.get('return_station')
        station = StationModel.objects.filter(id=station_id).first()
        if not station:
            return Response({"error": "Station not found."}, status=status.HTTP_400_BAD_REQUEST)

        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')
        if user_lat is None or user_lon is None:
            return Response({"error": "Latitude/longitude is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not is_near_station(user_lat, user_lon, station.latitude, station.longitude):
            return Response({"error": "You are not near the station."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Mark rental as COMPLETED, set return_station
            rental.status = RentalStatusChoices.COMPLETED
            rental.return_station = station
            rental.save()

            # Update vehicle
            vehicle = rental.car
            vehicle.status = VehicleStatusChoices.AVAILABLE
            vehicle.current_station = station
            vehicle.save()

        return Response({"message": "Car returned to station successfully."}, status=status.HTTP_200_OK)
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
            if ReservationModel.objects.filter(client=user, car=vehicle, status__in=[ReservationStatusChoices.PENDING, ReservationStatusChoices.CONFIRMED]).exists():
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