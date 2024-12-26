from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import UserModel


class UserTests(APITestCase):

    def setUp(self):
        self.register_url = reverse('register')
        self.verify_url = reverse('verify')
        self.login_url = reverse('login')
        self.me_url = reverse('me')
        self.change_password_url = reverse('change-password')
        self.reset_password_url = reverse('reset-password')
        self.reset_password_confirm_url = reverse('reset-password-confirm')

        self.valid_user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe",
            "password": "secret123!",
            "phone": "998901234567"  # 12 digits
        }

    def test_registration_success(self):
        """
        Ensure a user can register with valid data.
        """
        response = self.client.post(self.register_url, data=self.valid_user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('verification_id', response.data)
        self.assertIn('otp', response.data)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['username'], self.valid_user_data['username'])

    def test_registration_duplicate_username_for_verified_user(self):
        """
        If there's already a verified user with the same username,
        registration should fail.
        """
        # Create and verify a user
        user = UserModel.objects.create_user(**self.valid_user_data, is_verified=True)

        # Try registering again with the same username
        response = self.client.post(self.register_url, data=self.valid_user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_verify_user(self):
        """
        Test verifying a user with the correct OTP.
        """
        # Register user
        response = self.client.post(self.register_url, data=self.valid_user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        verification_id = response.data['verification_id']
        otp = response.data['otp']

        # Now verify
        verify_data = {
            "verification_id": verification_id,
            "code": otp
        }
        response_verify = self.client.post(self.verify_url, data=verify_data)
        self.assertEqual(response_verify.status_code, status.HTTP_200_OK)
        self.assertIn('message', response_verify.data)

        # Check that user is_verified is True
        user = UserModel.objects.get(username=self.valid_user_data['username'])
        self.assertTrue(user.is_verified)

    def test_verify_user_wrong_otp(self):
        # Register user
        response = self.client.post(self.register_url, data=self.valid_user_data)
        verification_id = response.data['verification_id']
        # Put a wrong OTP
        verify_data = {
            "verification_id": verification_id,
            "code": "9999"
        }
        response_verify = self.client.post(self.verify_url, data=verify_data)
        self.assertEqual(response_verify.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_unverified_user(self):
        """
        Unverified user shouldn't be able to login.
        """
        self.client.post(self.register_url, data=self.valid_user_data)
        login_data = {
            "username": "johndoe",
            "password": "secret123!"
        }
        response_login = self.client.post(self.login_url, data=login_data)
        self.assertEqual(response_login.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This user is not verified yet.', str(response_login.data))

    def test_login_verified_user(self):
        """
        Verified user can login and receive tokens.
        """
        # Register and verify
        response = self.client.post(self.register_url, data=self.valid_user_data)
        verification_id = response.data['verification_id']
        otp = response.data['otp']
        self.client.post(self.verify_url, data={
            "verification_id": verification_id,
            "code": otp
        })

        login_data = {
            "username": "johndoe",
            "password": "secret123!"
        }
        response_login = self.client.post(self.login_url, data=login_data)
        self.assertEqual(response_login.status_code, status.HTTP_200_OK)
        self.assertIn('refresh', response_login.data)
        self.assertIn('access', response_login.data)

    def test_get_me_unauthenticated(self):
        """
        Unauthenticated user should not be able to access /me/.
        """
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_me_authenticated(self):
        """
        Authenticated user should retrieve his own data.
        """
        # Register + verify + login
        response = self.client.post(self.register_url, data=self.valid_user_data)
        verification_id = response.data['verification_id']
        otp = response.data['otp']
        self.client.post(self.verify_url, data={
            "verification_id": verification_id,
            "code": otp
        })
        login_data = {
            "username": "johndoe",
            "password": "secret123!"
        }
        response_login = self.client.post(self.login_url, data=login_data)
        access_token = response_login.data['access']

        # Access /me/
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token)
        response_me = self.client.get(self.me_url)
        self.assertEqual(response_me.status_code, status.HTTP_200_OK)
        self.assertEqual(response_me.data['username'], self.valid_user_data['username'])

    def test_change_password(self):
        """
        Test changing password for a verified user.
        """
        # Register + verify + login
        response = self.client.post(self.register_url, data=self.valid_user_data)
        verification_id = response.data['verification_id']
        otp = response.data['otp']
        self.client.post(self.verify_url, data={
            "verification_id": verification_id,
            "code": otp
        })
        login_data = {
            "username": "johndoe",
            "password": "secret123!"
        }
        response_login = self.client.post(self.login_url, data=login_data)
        access_token = response_login.data['access']

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token)
        change_pw_data = {
            "old_password": "secret123!",
            "new_password": "NewSecret123!"
        }
        response_cp = self.client.post(self.change_password_url, data=change_pw_data)
        self.assertEqual(response_cp.status_code, status.HTTP_200_OK)

        # Logout and try to login with new password
        self.client.credentials()  # remove token
        new_login_data = {
            "username": "johndoe",
            "password": "NewSecret123!"
        }
        response_new_login = self.client.post(self.login_url, data=new_login_data)
        self.assertEqual(response_new_login.status_code, status.HTTP_200_OK)

    def test_reset_password_flow(self):
        """
        Test sending OTP to reset password using phone or username
        (depending on how you fix your actual code).
        """
        # Create a verified user
        user = UserModel.objects.create_user(**self.valid_user_data, is_verified=True)

        # Attempt reset
        reset_data = {
            "email_or_phone": user.phone  # or user.username if you fix the logic
        }
        response = self.client.post(self.reset_password_url, data=reset_data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertIn('verification_id', response.data)
        self.assertIn('otp', response.data)

        verification_id = response.data['verification_id']
        otp = response.data['otp']

        # Now confirm
        reset_confirm_data = {
            "verification_id": verification_id,
            "code": otp,
            "new_password": "ResetSecret123!"
        }
        response_confirm = self.client.post(self.reset_password_confirm_url, data=reset_confirm_data)
        self.assertEqual(response_confirm.status_code, status.HTTP_200_OK)

        # Ensure new password works
        login_data = {
            "username": "johndoe",
            "password": "ResetSecret123!"
        }
        response_login = self.client.post(self.login_url, data=login_data)
        self.assertEqual(response_login.status_code, status.HTTP_200_OK)
