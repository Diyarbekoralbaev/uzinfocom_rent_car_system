from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models import UserChoice, UserModel
from .models import StationModel
from .serializers import StationSerializer
from rest_framework_simplejwt.tokens import RefreshToken

class StationTestCase(TestCase):
    def setUp(self):
        """Set up test dependencies"""
        self.client = APIClient()

        # Create a test user
        self.user = UserModel.objects.create_user(
            username="testmanager",
            password="password123",
            role=UserChoice.MANAGER,
            is_staff=True,  # Required for role_required decorator
        )

        # Assign role
        self.user.role = UserChoice.MANAGER
        self.user.save()

        # Generate JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # Add Authorization header with JWT
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        # Create a test station
        self.station = StationModel.objects.create(
            name="Test Station",
            latitude=40.7128,
            longitude=-74.0060
        )

        self.valid_payload = {
            "name": "New Station",
            "latitude": 34.0522,
            "longitude": -118.2437
        }

        self.invalid_payload = {
            "name": "",
            "latitude": "invalid_latitude",
            "longitude": "invalid_longitude"
        }

    def test_get_stations(self):
        """Test retrieving a list of stations"""
        response = self.client.get("/stations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), StationModel.objects.count())

    def test_get_station_detail(self):
        """Test retrieving a single station's details"""
        response = self.client.get(f"/stations/{self.station.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.station.name)

    def test_create_station(self):
        """Test creating a new station"""
        response = self.client.post("/stations/", data=self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StationModel.objects.count(), 2)
        self.assertEqual(response.data["name"], self.valid_payload["name"])

    def test_create_station_invalid(self):
        """Test creating a new station with invalid data"""
        response = self.client.post("/stations/", data=self.invalid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_station(self):
        """Test updating an existing station"""
        updated_data = {
            "name": "Updated Station",
            "latitude": 40.7306,
            "longitude": -73.9352
        }
        response = self.client.put(f"/stations/{self.station.id}/", data=updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.station.refresh_from_db()
        self.assertEqual(self.station.name, updated_data["name"])

    def test_delete_station(self):
        """Test deleting a station"""
        response = self.client.delete(f"/stations/{self.station.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StationModel.objects.count(), 0)

    def test_serializer_valid_data(self):
        """Test serializer with valid data"""
        serializer = StationSerializer(data=self.valid_payload)
        self.assertTrue(serializer.is_valid())

    def test_serializer_invalid_data(self):
        """Test serializer with invalid data"""
        serializer = StationSerializer(data=self.invalid_payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)
        self.assertIn("latitude", serializer.errors)
        self.assertIn("longitude", serializer.errors)
