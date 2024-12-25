from django.db import transaction
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAuthenticatedClientOrManager, IsManager
from stations.models import StationModel
from users.models import UserChoice, UserModel
from vehicles.models import VehicleModel, VehicleStatusChoices
from .models import RentalModel, ReservationModel, RentalStatusChoices, ReservationStatusChoices
from .serializers import RentalSerializer, ReservationSerializer
from .utils import is_near_station, send_email


@method_decorator(gzip_page, name='dispatch')
class RentalViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing rental instances.
    """
    serializer_class = RentalSerializer
    permission_classes = [IsAuthenticatedClientOrManager]
    queryset = RentalModel.objects.select_related('car', 'client', 'pickup_station', 'return_station').all()

    def get_queryset(self):
        """
        Override the default `get_queryset` to handle filtering based on user role.
        """
        user = self.request.user
        if user.is_authenticated and user.role == UserChoice.CLIENT:
            return self.queryset.filter(client=user)
        elif user.is_authenticated and user.role == UserChoice.MANAGER:
            return self.queryset.all()
        return RentalModel.objects.none()

    def perform_create(self, serializer):
        """
        Handle rental creation within an atomic transaction.
        """
        with transaction.atomic():
            user = UserModel.objects.select_for_update().get(id=self.request.user.id)
            car = VehicleModel.objects.select_for_update().get(id=self.request.data['car'])

            # Ensure client does not have an active rental
            if RentalModel.objects.filter(client=user, status=RentalStatusChoices.ACTIVE).exists():
                raise serializers.ValidationError("You already have an active rental.")

            # Check for confirmed reservation overlap
            start_date = serializer.validated_data['start_date']
            end_date = serializer.validated_data['end_date']
            if ReservationModel.objects.filter(
                    car=car,
                    start_date__lte=end_date,
                    end_date__gte=start_date,
                    status=ReservationStatusChoices.CONFIRMED
            ).exists():
                raise serializers.ValidationError(
                    "This car is reserved for that period. Please choose another car or time."
                )

            # Calculate total amount
            daily_price = car.daily_price
            day_count = (end_date.date() - start_date.date()).days or 1  # Minimum 1 day
            total_amount = daily_price * day_count

            # Check user balance
            if user.balance < total_amount:
                raise serializers.ValidationError("Insufficient balance.")

            # Deduct balance
            user.balance = F('balance') - total_amount
            user.save()

            # Save rental
            rental = serializer.save(
                client=user,
                status=RentalStatusChoices.PENDING,
                total_amount=total_amount
            )

            # Send email notification
            send_email(
                subject="Rental Request",
                to_email=user.email,
                message=f"Your rental request for {car} has been received. Please wait for manager approval."
            )

    def perform_update(self, serializer):
        """
        Handle rental updates with role-based permissions.
        """
        user = self.request.user
        rental = self.get_object()

        if user.role == UserChoice.CLIENT:
            # Clients can only cancel or update their own rentals
            new_status = self.request.data.get('status')
            if new_status == RentalStatusChoices.CANCELLED and rental.status == RentalStatusChoices.PENDING:
                with transaction.atomic():
                    rental.status = RentalStatusChoices.CANCELLED
                    rental.save()

                    # Refund user
                    user.balance = F('balance') + rental.total_amount
                    user.save()

                    # Update vehicle status
                    rental.car.status = VehicleStatusChoices.AVAILABLE
                    rental.car.save()

                    # Send email
                    send_email(
                        subject="Rental Cancelled",
                        to_email=user.email,
                        message=f"Your rental for {rental.car} has been cancelled."
                    )
                serializer.instance = rental
                return Response(RentalSerializer(rental).data, status=status.HTTP_200_OK)
            else:
                raise serializers.ValidationError("Invalid status transition.")
        elif user.role == UserChoice.MANAGER:
            # Managers can update rentals as needed
            return super().perform_update(serializer)
        else:
            raise serializers.ValidationError("You do not have permission to update this rental.")

    def destroy(self, request, *args, **kwargs):
        user = request.user
        rental = self.get_object()

        if user.role == UserChoice.MANAGER:
            # Managers can delete rentals
            with transaction.atomic():
                # Refund user if rental was active or pending
                if rental.status in [RentalStatusChoices.PENDING, RentalStatusChoices.ACTIVE]:
                    rental.client.balance = F('balance') + rental.total_amount
                    rental.client.save()

                # Update vehicle status
                rental.car.status = VehicleStatusChoices.AVAILABLE
                rental.car.save()

                # Delete rental
                rental.delete()

                # Send email
                send_email(
                    subject="Rental Deleted",
                    to_email=rental.client.email,
                    message=f"Your rental for {rental.car} has been deleted by the manager."
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif user.role == UserChoice.CLIENT:
            if rental.status == RentalStatusChoices.PENDING:
                with transaction.atomic():
                    rental.status = RentalStatusChoices.CANCELLED
                    rental.save()

                    # Refund user
                    rental.client.balance = F('balance') + rental.total_amount
                    rental.client.save()

                    # Update vehicle status
                    rental.car.status = VehicleStatusChoices.AVAILABLE
                    rental.car.save()

                    # Send email
                    send_email(
                        subject="Rental Cancelled",
                        to_email=user.email,
                        message=f"Your rental for {rental.car} has been cancelled."
                    )
                return Response(RentalSerializer(rental).data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "You can only cancel rentals that are pending."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response({"error": "You do not have permission to delete this rental."},
                            status=status.HTTP_403_FORBIDDEN)

    @swagger_auto_schema(
        operation_id="set_rental_status",
        operation_summary="Set rental status",
        operation_description="Allows managers to set the status of a rental.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[choice[0] for choice in RentalStatusChoices.choices],
                    description='New status for the rental'
                )
            }
        ),
        responses={
            200: RentalSerializer(),
            400: "Bad Request",
            403: "Forbidden"
        }
    )
    @action(detail=True, methods=['post'], url_path='set-status', permission_classes=[IsManager])
    def set_status(self, request, pk=None):
        """
        Manager can forcibly set rental status if allowed transitions.
        """
        with transaction.atomic():
            rental = RentalModel.objects.select_for_update().get(pk=pk)
            new_status = request.data.get('status')

            if not rental.can_transition_to(new_status):
                return Response(
                    {"error": f"Cannot transition from {rental.status} to {new_status}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_status == RentalStatusChoices.ACTIVE:
                # Check for overlapping reservations
                if ReservationModel.objects.filter(
                        car=rental.car,
                        start_date__lte=rental.end_date,
                        end_date__gte=rental.start_date,
                        status=ReservationStatusChoices.CONFIRMED
                ).exists():
                    return Response(
                        {"error": "This car is already reserved during this period."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                rental.car.status = VehicleStatusChoices.RENTED
            elif new_status == RentalStatusChoices.COMPLETED:
                if not rental.return_station:
                    return Response(
                        {"error": "Set return_station before completing the rental."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                rental.car.status = VehicleStatusChoices.AVAILABLE
            elif new_status == RentalStatusChoices.CANCELLED:
                # Refund user if necessary
                rental.client.balance = F('balance') + rental.total_amount
                rental.client.save()
                rental.car.status = VehicleStatusChoices.AVAILABLE

            rental.status = new_status
            rental.save()
            rental.car.save()

            # Send email notification
            send_email(
                subject="Rental Status Updated",
                to_email=rental.client.email,
                message=f"Your rental for {rental.car} has been updated to {new_status}."
            )

            return Response(RentalSerializer(rental).data, status=status.HTTP_200_OK)

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
    @action(detail=False, methods=['post'], url_path='return-car-to-station',
            permission_classes=[IsAuthenticatedClientOrManager])
    def return_car_to_station(self, request):
        """
        Client returns the car to a station, verifying they are physically near the station.
        """
        user = request.user
        if user.role != UserChoice.CLIENT:
            return Response({"error": "You do not have permission to return a car."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            rental = RentalModel.objects.select_for_update().get(client=user, status=RentalStatusChoices.ACTIVE)
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

        # Send email notification
        send_email(
            subject="Car Returned",
            to_email=user.email,
            message=f"Your rental for {vehicle} has been completed. Thank you for using our service."
        )

        return Response({"message": "Car returned to station successfully."}, status=status.HTTP_200_OK)


@method_decorator(gzip_page, name='dispatch')
class ReservationViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing reservation instances.
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticatedClientOrManager]
    queryset = ReservationModel.objects.select_related('car', 'client').all()
    http_method_names = ['get', 'post']

    def get_queryset(self):
        """
        Override the default `get_queryset` to handle filtering based on user role.
        """
        user = self.request.user
        if user.is_authenticated and user.role == UserChoice.CLIENT:
            return self.queryset.filter(client=user)
        elif user.is_authenticated and user.role == UserChoice.MANAGER:
            return self.queryset.all()
        return ReservationModel.objects.none()

    def perform_create(self, serializer):
        """
        Handle reservation creation with necessary validations.
        """
        with transaction.atomic():
            user = self.request.user
            car = serializer.validated_data['car']
            start_date = serializer.validated_data['start_date']
            end_date = serializer.validated_data['end_date']

            # Check if the user already has a PENDING or CONFIRMED reservation for the same car
            if ReservationModel.objects.filter(
                    client=user,
                    car=car,
                    status__in=[ReservationStatusChoices.PENDING, ReservationStatusChoices.CONFIRMED],
                    start_date__lte=end_date,
                    end_date__gte=start_date
            ).exists():
                raise serializers.ValidationError(
                    "You already have a reservation for this car during the selected period."
                )

            # Check for active rentals that conflict
            if RentalModel.objects.filter(
                    car=car,
                    status=RentalStatusChoices.ACTIVE,
                    start_date__lte=end_date,
                    end_date__gte=start_date
            ).exists():
                raise serializers.ValidationError(
                    "This car is already rented during the selected period."
                )

            # Save reservation
            reservation = serializer.save(
                client=user,
                status=ReservationStatusChoices.PENDING
            )

            # Send email notification
            send_email(
                subject="Reservation Request",
                to_email=user.email,
                message=f"Your reservation request for {car} has been received. Please wait for manager approval."
            )

    def update(self, request, *args, **kwargs):
        """Disable full updates for reservations."""
        return Response({"error": "Update not allowed for reservations."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        """Disable partial updates for reservations."""
        return Response({"error": "Partial update not allowed for reservations."},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        """Disable deletion for reservations."""
        return Response({"error": "Delete not allowed for reservations."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @swagger_auto_schema(
        operation_id="set_reservation_status",
        operation_summary="Set reservation status",
        operation_description="Allows managers to set the status of a reservation.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[choice[0] for choice in ReservationStatusChoices.choices],
                    description='New status for the reservation'
                )
            }
        ),
        responses={
            200: ReservationSerializer(),
            400: "Bad Request",
            403: "Forbidden"
        }
    )
    @action(detail=True, methods=['post'], url_path='set-status', permission_classes=[IsManager])
    def set_status(self, request, pk=None):
        """
        Manager can set a reservation's status to CONFIRMED, CANCELLED, etc.
        """
        with transaction.atomic():
            reservation = ReservationModel.objects.select_for_update().get(pk=pk)
            new_status = request.data.get('status')

            # Define valid statuses
            valid_statuses = [choice[0] for choice in ReservationStatusChoices.choices]
            if new_status not in valid_statuses:
                return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

            # Define valid transitions
            valid_transitions = {
                ReservationStatusChoices.PENDING: [ReservationStatusChoices.CONFIRMED,
                                                   ReservationStatusChoices.CANCELLED],
                ReservationStatusChoices.CONFIRMED: [ReservationStatusChoices.CANCELLED],
                ReservationStatusChoices.CANCELLED: []
            }

            if new_status not in valid_transitions.get(reservation.status, []):
                return Response(
                    {"error": f"Cannot transition from {reservation.status} to {new_status}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # If confirming, check for overlapping confirmed reservations or active rentals
            if new_status == ReservationStatusChoices.CONFIRMED:
                # Check for overlapping confirmed reservations
                if ReservationModel.objects.filter(
                        car=reservation.car,
                        status=ReservationStatusChoices.CONFIRMED,
                        start_date__lte=reservation.end_date,
                        end_date__gte=reservation.start_date
                ).exclude(pk=pk).exists():
                    return Response(
                        {"error": "Another confirmed reservation overlaps this period."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check for overlapping active rentals
                if RentalModel.objects.filter(
                        car=reservation.car,
                        status=RentalStatusChoices.ACTIVE,
                        start_date__lte=reservation.end_date,
                        end_date__gte=reservation.start_date
                ).exists():
                    return Response(
                        {"error": "This car is currently rented during the selected period."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Update reservation status
            reservation.status = new_status
            reservation.save()

            # Send email notification
            send_email(
                subject="Reservation Status Updated",
                to_email=reservation.client.email,
                message=f"Your reservation for {reservation.car} has been updated to {new_status}."
            )

            return Response(ReservationSerializer(reservation).data, status=status.HTTP_200_OK)
