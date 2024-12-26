from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models import UserChoice, UserModel
from vehicles.models import VehicleModel, VehicleStatusChoices
from stations.models import StationModel  # Assuming stations app has StationModel
from vehicles.serializers import VehicleSerializer, VehicleAvailabilitySerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse


class VehicleTestCase(TestCase):
    def setUp(self):
        """Set up test dependencies"""
        self.client_manager = APIClient()
        self.client_client = APIClient()

        # Create a manager user
        self.manager_user = UserModel.objects.create_user(
            username="testmanager",
            password="password123",
            email="testmanager@example.com",
            role=UserChoice.MANAGER,
            is_staff=True,  # Required for role_required decorator if used
        )

        # Create a client user
        self.client_user = UserModel.objects.create_user(
            username="testclient",
            password="password123",
            email="testclient@example.com",
            role=UserChoice.CLIENT,
            is_staff=False,
        )

        # Generate JWT tokens
        refresh_manager = RefreshToken.for_user(self.manager_user)
        self.access_token_manager = str(refresh_manager.access_token)

        refresh_client = RefreshToken.for_user(self.client_user)
        self.access_token_client = str(refresh_client.access_token)

        # Authenticate clients
        self.client_manager.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token_manager}")
        self.client_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token_client}")

        # Create a test station
        self.station = StationModel.objects.create(
            name="Test Station",
            latitude=40.7128,
            longitude=-74.0060
        )

        # Create vehicles
        self.vehicle1 = VehicleModel.objects.create(
            brand="Toyota",
            model="Corolla",
            daily_price=30.00,
            status=VehicleStatusChoices.AVAILABLE,
            current_station=self.station
        )
        self.vehicle2 = VehicleModel.objects.create(
            brand="Honda",
            model="Civic",
            daily_price=35.00,
            status=VehicleStatusChoices.RENTED,
            current_station=self.station
        )

        # Define URLs using reverse for better URL management
        self.list_url = reverse('vehicle-list')  # Ensure your router names this route
        self.detail_url = reverse('vehicle-detail', kwargs={'pk': self.vehicle1.id})
        self.set_status_url = reverse('vehicle-set-status', kwargs={'pk': self.vehicle1.id})

        # Valid and invalid payloads for creating/updating vehicles
        self.valid_payload = {
            "brand": "Ford",
            "model": "Focus",
            "daily_price": 25.50,  # Changed to float
            "status": VehicleStatusChoices.AVAILABLE,
            "current_station": self.station.id
        }

        self.invalid_payload = {
            "brand": "",
            "model": "",
            "daily_price": -10.0,  # Changed to negative float
            "status": "XX",  # Invalid status
            "current_station": None
        }

        # Payloads for setting vehicle status
        self.valid_status_payload = {
            "status": VehicleStatusChoices.MAINTENANCE
        }

        self.invalid_status_payload = {
            "status": "XX"  # Invalid status
        }

    # -----------------------------
    # Permission and CRUD Tests
    # -----------------------------

    def test_manager_can_list_all_vehicles(self):
        """Test that a manager can retrieve all vehicles"""
        response = self.client_manager.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), VehicleModel.objects.count())

    def test_client_can_list_only_available_vehicles(self):
        """Test that a client can retrieve only available vehicles"""
        response = self.client_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        available_vehicles = VehicleModel.objects.filter(status=VehicleStatusChoices.AVAILABLE)
        self.assertEqual(len(response.data), available_vehicles.count())
        for vehicle in response.data:
            self.assertEqual(vehicle['status'], VehicleStatusChoices.AVAILABLE)

    def test_manager_can_retrieve_vehicle_detail(self):
        """Test that a manager can retrieve a vehicle's details"""
        response = self.client_manager.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vehicle = VehicleModel.objects.get(id=self.vehicle1.id)
        serializer = VehicleSerializer(vehicle)
        self.assertEqual(response.data, serializer.data)

    def test_client_can_retrieve_available_vehicle_detail(self):
        """Test that a client can retrieve details of an available vehicle"""
        response = self.client_client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.vehicle1.id)

    def test_client_cannot_retrieve_rented_vehicle_detail(self):
        """Test that a client cannot retrieve details of a rented vehicle"""
        rented_vehicle_url = reverse('vehicle-detail', kwargs={'pk': self.vehicle2.id})
        response = self.client_client.get(rented_vehicle_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_create_vehicle(self):
        """Test that a manager can create a new vehicle"""
        response = self.client_manager.post(self.list_url, data=self.valid_payload, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print("Create Vehicle Error Response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VehicleModel.objects.count(), 3)
        self.assertEqual(response.data['brand'], self.valid_payload['brand'])
        self.assertEqual(response.data['model'], self.valid_payload['model'])

    def test_client_cannot_create_vehicle(self):
        """Test that a client cannot create a new vehicle"""
        response = self.client_client.post(self.list_url, data=self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(VehicleModel.objects.count(), 2)

    def test_manager_can_update_vehicle(self):
        """Test that a manager can update an existing vehicle"""
        updated_data = {
            "brand": "Toyota",
            "model": "Corolla Updated",
            "daily_price": 32.00,  # Changed to float
            "status": VehicleStatusChoices.RENTED,
            "current_station": self.station.id
        }
        response = self.client_manager.put(self.detail_url, data=updated_data, format='json')
        if response.status_code != status.HTTP_200_OK:
            print("Update Vehicle Error Response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.model, updated_data['model'])
        self.assertEqual(self.vehicle1.daily_price, updated_data['daily_price'])
        self.assertEqual(self.vehicle1.status, updated_data['status'])

    def test_client_cannot_update_vehicle(self):
        """Test that a client cannot update an existing vehicle"""
        updated_data = {
            "brand": "Toyota",
            "model": "Corolla Updated",
            "daily_price": 32.00,  # Changed to float
            "status": VehicleStatusChoices.RENTED,
            "current_station": self.station.id
        }
        response = self.client_client.put(self.detail_url, data=updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.vehicle1.refresh_from_db()
        self.assertNotEqual(self.vehicle1.model, updated_data['model'])

    def test_manager_can_partial_update_vehicle(self):
        """Test that a manager can partially update a vehicle"""
        partial_data = {
            "daily_price": 28.00  # Changed to float
        }
        response = self.client_manager.patch(self.detail_url, data=partial_data, format='json')
        if response.status_code != status.HTTP_200_OK:
            print("Partial Update Vehicle Error Response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.daily_price, partial_data['daily_price'])

    def test_client_cannot_partial_update_vehicle(self):
        """Test that a client cannot partially update a vehicle"""
        partial_data = {
            "daily_price": 28.00  # Changed to float
        }
        response = self.client_client.patch(self.detail_url, data=partial_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.vehicle1.refresh_from_db()
        self.assertNotEqual(self.vehicle1.daily_price, partial_data['daily_price'])

    def test_manager_can_delete_vehicle(self):
        """Test that a manager can delete a vehicle"""
        response = self.client_manager.delete(self.detail_url)
        if response.status_code != status.HTTP_204_NO_CONTENT:
            print("Delete Vehicle Error Response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(VehicleModel.objects.count(), 1)

    def test_client_cannot_delete_vehicle(self):
        """Test that a client cannot delete a vehicle"""
        response = self.client_client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(VehicleModel.objects.count(), 2)

    # -----------------------------
    # Set Status Endpoint Tests
    # -----------------------------

    def test_manager_can_set_vehicle_status(self):
        """Test that a manager can set the status of a vehicle"""
        response = self.client_manager.post(self.set_status_url, data=self.valid_status_payload, format='json')
        if response.status_code != status.HTTP_200_OK:
            print("Set Status Error Response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.status, self.valid_status_payload['status'])

    def test_client_cannot_set_vehicle_status(self):
        """Test that a client cannot set the status of a vehicle"""
        response = self.client_client.post(self.set_status_url, data=self.valid_status_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.vehicle1.refresh_from_db()
        self.assertNotEqual(self.vehicle1.status, self.valid_status_payload['status'])

    def test_set_status_with_invalid_data(self):
        """Test setting vehicle status with invalid data"""
        response = self.client_manager.post(self.set_status_url, data=self.invalid_status_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    # -----------------------------
    # Serializer Tests
    # -----------------------------

    def test_serializer_valid_data(self):
        """Test VehicleSerializer with valid data"""
        serializer = VehicleSerializer(data=self.valid_payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_invalid_data(self):
        """Test VehicleSerializer with invalid data"""
        serializer = VehicleSerializer(data=self.invalid_payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('brand', serializer.errors)
        self.assertIn('model', serializer.errors)
        self.assertIn('daily_price', serializer.errors)
        self.assertIn('status', serializer.errors)
        self.assertIn('current_station', serializer.errors)

    # -----------------------------
    # Model Tests
    # -----------------------------

    def test_vehicle_str_method(self):
        """Test the __str__ method of VehicleModel"""
        self.assertEqual(str(self.vehicle1), f"{self.vehicle1.brand} {self.vehicle1.model}")

    # -----------------------------
    # Queryset Tests
    # -----------------------------

    def test_vehicle_queryset_manager(self):
        """Test that manager can access all vehicles"""
        response = self.client_manager.get(self.list_url)
        self.assertEqual(len(response.data), VehicleModel.objects.count())

    def test_vehicle_queryset_client(self):
        """Test that client can access only available vehicles"""
        response = self.client_client.get(self.list_url)
        available_count = VehicleModel.objects.filter(status=VehicleStatusChoices.AVAILABLE).count()
        self.assertEqual(len(response.data), available_count)

    # -----------------------------
    # Endpoint Method Tests
    # -----------------------------

    def test_set_status_endpoint_requires_post_method(self):
        """Test that set-status endpoint only accepts POST requests"""
        response = self.client_manager.get(self.set_status_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # -----------------------------
    # Role-Based Permission Tests
    # -----------------------------

    def test_vehicle_creation_requires_manager_role(self):
        """Ensure that only users with manager role can create vehicles"""
        # Attempt to create vehicle with client credentials
        response = self.client_client.post(self.list_url, data=self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_vehicle_update_requires_manager_role(self):
        """Ensure that only users with manager role can update vehicles"""
        # Attempt to update vehicle with client credentials
        updated_data = {"model": "Updated Model"}
        response = self.client_client.patch(self.detail_url, data=updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_vehicle_delete_requires_manager_role(self):
        """Ensure that only users with manager role can delete vehicles"""
        # Attempt to delete vehicle with client credentials
        response = self.client_client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_set_status_requires_manager_role(self):
        """Ensure that only users with manager role can set vehicle status"""
        # Attempt to set status with client credentials
        response = self.client_client.post(self.set_status_url, data=self.valid_status_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

