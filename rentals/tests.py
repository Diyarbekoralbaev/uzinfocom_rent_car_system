# tests.py

import datetime
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import UserModel, UserChoice
from stations.models import StationModel
from vehicles.models import VehicleModel, VehicleStatusChoices
from .models import (
    RentalModel,
    ReservationModel,
    RentalStatusChoices,
    ReservationStatusChoices,
)


class RentalAppTestBase(APITestCase):
    """
    Base test class that sets up:
      - A manager user
      - A client user
      - An active station
      - A vehicle
      - Two API clients authenticated via Simple JWT
    """

    def setUp(self):
        # Create users
        self.manager_user = UserModel.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='managerpass',
            role=UserChoice.MANAGER,
            balance=10000,
            is_verified=True
        )
        self.client_user = UserModel.objects.create_user(
            username='client',
            email='client@test.com',
            password='clientpass',
            role=UserChoice.CLIENT,
            balance=5000,
            is_verified=True
        )

        # Create an active station
        self.station = StationModel.objects.create(
            name="Main Station",
            latitude=40.7128,
            longitude=-74.0060,
            is_active=True
        )

        # Create a vehicle
        self.vehicle = VehicleModel.objects.create(
            brand="Toyota",
            model="Corolla",
            daily_price=100,
            status=VehicleStatusChoices.AVAILABLE,
            current_station=self.station
        )

        # Create API clients with JWT credentials
        manager_token = RefreshToken.for_user(self.manager_user)
        self.client_manager = APIClient()
        self.client_manager.credentials(
            HTTP_AUTHORIZATION=f'Bearer {manager_token.access_token}'
        )

        client_token = RefreshToken.for_user(self.client_user)
        self.client_client = APIClient()
        self.client_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {client_token.access_token}'
        )


class TestRentalViewSet(RentalAppTestBase):
    """
    Test cases for RentalViewSet endpoints.
    """

    def test_create_rental_success(self):
        """
        A verified client with sufficient balance should be able to create a new rental.
        """
        url = reverse('rentalmodel-list')  # Adjust to your actual route name
        start_date = timezone.now() + datetime.timedelta(days=1)
        end_date = timezone.now() + datetime.timedelta(days=2)

        payload = {
            "car": self.vehicle.id,
            "pickup_station": self.station.id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        rental = RentalModel.objects.last()
        self.assertIsNotNone(rental)
        self.assertEqual(rental.client, self.client_user)
        self.assertEqual(rental.car, self.vehicle)
        self.assertEqual(rental.status, RentalStatusChoices.PENDING)
        # Check that the user balance has been deducted
        self.client_user.refresh_from_db()
        self.assertLess(self.client_user.balance, 5000)

    def test_create_rental_insufficient_balance(self):
        """
        If a client does not have sufficient balance, rental creation should fail.
        """
        self.client_user.balance = 10
        self.client_user.save()

        url = reverse('rentalmodel-list')
        start_date = timezone.now() + datetime.timedelta(days=1)
        end_date = timezone.now() + datetime.timedelta(days=2)

        payload = {
            "car": self.vehicle.id,
            "pickup_station": self.station.id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("Insufficient balance", str(response.data))

    def test_create_rental_past_date(self):
        """
        Rental start_date must not be in the past.
        """
        url = reverse('rentalmodel-list')
        start_date = timezone.now() - datetime.timedelta(days=1)
        end_date = timezone.now() + datetime.timedelta(days=2)

        payload = {
            "car": self.vehicle.id,
            "pickup_station": self.station.id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("Cannot rent a car in the past", str(response.data))

    def test_client_cancel_pending_rental(self):
        # Original user balance is 5000
        old_balance = self.client_user.balance

        # STEP 1: Create rental via POST
        url = reverse('rentalmodel-list')
        payload = {
            "car": self.vehicle.id,
            "pickup_station": self.station.id,
            "start_date": (timezone.now() + datetime.timedelta(days=1)).isoformat(),
            "end_date": (timezone.now() + datetime.timedelta(days=3)).isoformat(),
        }
        create_response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)

        # The user is now charged in perform_create()
        self.client_user.refresh_from_db()
        # If total_amount was 200, user.balance should be 5000 - 200 = 4800
        self.assertEqual(self.client_user.balance, old_balance - 200)

        # STEP 2: Cancel the rental
        rental_id = create_response.data["id"]
        detail_url = reverse('rentalmodel-detail', args=[rental_id])
        cancel_response = self.client_client.patch(
            detail_url,
            data={"status": RentalStatusChoices.CANCELLED},
            format='json'
        )
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK, cancel_response.data)

        # Now they should have been refunded 200
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.balance, old_balance)

    def test_client_cannot_cancel_active_rental_via_update(self):
        """
        A client cannot cancel an ACTIVE rental via the same update endpoint (invalid transition).
        """
        rental = RentalModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            pickup_station=self.station,
            start_date=timezone.now() + datetime.timedelta(days=1),
            end_date=timezone.now() + datetime.timedelta(days=2),
            total_amount=200,
            status=RentalStatusChoices.ACTIVE
        )

        url = reverse('rentalmodel-detail', args=[rental.id])
        response = self.client_client.patch(url, data={"status": RentalStatusChoices.CANCELLED}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("Invalid status transition", str(response.data))

    def test_manager_update_rental(self):
        """
        Managers can update rental attributes (e.g. changing end_date).
        """
        rental = RentalModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            pickup_station=self.station,
            start_date=timezone.now() + datetime.timedelta(days=1),
            end_date=timezone.now() + datetime.timedelta(days=2),
            total_amount=300,
            status=RentalStatusChoices.PENDING
        )
        new_end_date = (timezone.now() + datetime.timedelta(days=3)).isoformat()
        url = reverse('rentalmodel-detail', args=[rental.id])
        payload = {
            "end_date": new_end_date
        }
        response = self.client_manager.patch(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        rental.refresh_from_db()
        # Compare date/time truncated to seconds for equality
        self.assertEqual(rental.end_date.isoformat()[:19], new_end_date[:19])

    def test_manager_delete_rental_pending(self):
        """
        A manager can delete a PENDING rental, refunding the user, and marking vehicle as available.
        """
        rental = RentalModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            pickup_station=self.station,
            start_date=timezone.now() + datetime.timedelta(days=1),
            end_date=timezone.now() + datetime.timedelta(days=2),
            total_amount=200,
            status=RentalStatusChoices.PENDING
        )
        old_balance = self.client_user.balance
        url = reverse('rentalmodel-detail', args=[rental.id])
        response = self.client_manager.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        # Verify it's deleted
        self.assertFalse(RentalModel.objects.filter(id=rental.id).exists())

        # Check user’s balance refunded
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.balance, old_balance + 200)

        # Vehicle is available
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatusChoices.AVAILABLE)

    def test_manager_set_rental_status_active(self):
        """
        Manager can set rental status to ACTIVE via set-status endpoint.
        """
        rental = RentalModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            pickup_station=self.station,
            start_date=timezone.now() + datetime.timedelta(days=1),
            end_date=timezone.now() + datetime.timedelta(days=2),
            total_amount=200,
            status=RentalStatusChoices.PENDING
        )
        url = reverse('rentalmodel-set-status', args=[rental.id])
        payload = {"status": RentalStatusChoices.ACTIVE}
        response = self.client_manager.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        rental.refresh_from_db()
        self.assertEqual(rental.status, RentalStatusChoices.ACTIVE)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatusChoices.RENTED)

    def test_client_return_car_to_station_success(self):
        """
        Client returns the car to a station. Must have an ACTIVE rental, must be near the station.
        """
        rental = RentalModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            pickup_station=self.station,
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=1),
            total_amount=100,
            status=RentalStatusChoices.ACTIVE
        )
        # We assume the user is 'near' the station (matching lat/lon)
        url = reverse('rentalmodel-return-car-to-station')
        payload = {
            "return_station": self.station.id,
            "latitude": float(self.station.latitude),  # exact match
            "longitude": float(self.station.longitude)  # exact match
        }
        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        rental.refresh_from_db()
        self.assertEqual(rental.status, RentalStatusChoices.COMPLETED)
        self.assertEqual(rental.return_station, self.station)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, VehicleStatusChoices.AVAILABLE)
        self.assertEqual(self.vehicle.current_station, self.station)

    def test_client_return_car_to_station_wrong_location(self):
        """
        If user is not near the station, returning the car should fail.
        """
        rental = RentalModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            pickup_station=self.station,
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=1),
            total_amount=100,
            status=RentalStatusChoices.ACTIVE
        )
        url = reverse('rentalmodel-return-car-to-station')
        payload = {
            "return_station": self.station.id,
            "latitude": 0.0,  # far from station
            "longitude": 0.0
        }
        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You are not near the station.", str(response.data))


class TestReservationViewSet(RentalAppTestBase):
    """
    Test cases for ReservationViewSet endpoints.
    """

    def test_create_reservation_success(self):
        """
        A verified client can create a reservation for an available vehicle in a valid period.
        """
        url = reverse('reservationmodel-list')  # e.g. "/reservations/"
        start_date = timezone.now() + datetime.timedelta(days=2)
        end_date = timezone.now() + datetime.timedelta(days=3)
        payload = {
            "car": self.vehicle.id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        reservation = ReservationModel.objects.last()
        self.assertIsNotNone(reservation)
        self.assertEqual(reservation.client, self.client_user)
        self.assertEqual(reservation.car, self.vehicle)
        self.assertEqual(reservation.status, ReservationStatusChoices.PENDING)

    def test_create_reservation_in_the_past(self):
        """
        Reservation start_date cannot be in the past.
        """
        url = reverse('reservationmodel-list')
        start_date = timezone.now() - datetime.timedelta(days=1)
        end_date = timezone.now() + datetime.timedelta(days=1)
        payload = {
            "car": self.vehicle.id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot reserve a car in the past", str(response.data))

    def test_create_overlapping_reservation_for_same_car(self):
        """
        Cannot create a reservation overlapping an existing PENDING/CONFIRMED reservation for the same car.
        """
        ReservationModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            start_date=timezone.now() + datetime.timedelta(days=1),
            end_date=timezone.now() + datetime.timedelta(days=2),
            status=ReservationStatusChoices.PENDING
        )

        url = reverse('reservationmodel-list')
        payload = {
            "car": self.vehicle.id,
            "start_date": (timezone.now() + datetime.timedelta(days=1)).isoformat(),
            "end_date": (timezone.now() + datetime.timedelta(days=2)).isoformat(),
        }
        response = self.client_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You already have a reservation for this car", str(response.data))

    def test_manager_confirm_reservation(self):
        """
        Manager can confirm a PENDING reservation if no overlapping confirmed reservations or active rentals.
        """
        reservation = ReservationModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            start_date=timezone.now() + datetime.timedelta(days=3),
            end_date=timezone.now() + datetime.timedelta(days=4),
            status=ReservationStatusChoices.PENDING
        )
        url = reverse('reservationmodel-set-status', args=[reservation.id])
        payload = {"status": ReservationStatusChoices.CONFIRMED}
        response = self.client_manager.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, ReservationStatusChoices.CONFIRMED)

    def test_manager_cancel_reservation(self):
        """
        Manager can cancel a PENDING or CONFIRMED reservation.
        """
        reservation = ReservationModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            start_date=timezone.now() + datetime.timedelta(days=3),
            end_date=timezone.now() + datetime.timedelta(days=4),
            status=ReservationStatusChoices.CONFIRMED
        )
        url = reverse('reservationmodel-set-status', args=[reservation.id])
        payload = {"status": ReservationStatusChoices.CANCELLED}
        response = self.client_manager.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, ReservationStatusChoices.CANCELLED)

    def test_client_cannot_update_reservation(self):
        """
        Client attempting to update or delete a reservation should not be allowed (405).
        """
        reservation = ReservationModel.objects.create(
            client=self.client_user,
            car=self.vehicle,
            start_date=timezone.now() + datetime.timedelta(days=3),
            end_date=timezone.now() + datetime.timedelta(days=4),
            status=ReservationStatusChoices.PENDING
        )
        url = reverse('reservationmodel-detail', args=[reservation.id])

        # Attempt partial update
        response = self.client_client.patch(url, data={"status": ReservationStatusChoices.CONFIRMED}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)

        # Attempt delete
        response = self.client_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)
