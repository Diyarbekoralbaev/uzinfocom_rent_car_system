# payments/tests.py

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import UserModel, UserChoice
from payments.models import PaymentModel, PaymentStatusChoices


class PaymentAPITestCase(APITestCase):
    def setUp(self):
        """
        Create a client user and a manager user with unique phone & email
        to satisfy the unique constraints.
        """
        # Create a verified client
        self.client_user = UserModel.objects.create_user(
            username='client_user',
            password='client_pass',
            role=UserChoice.CLIENT,
            is_verified=True,
            email='client@example.com',      # MUST be unique
            phone='998000000001',            # 12 digits for phone, also unique
            balance=0
        )

        # Create a verified manager
        self.manager_user = UserModel.objects.create_user(
            username='manager_user',
            password='manager_pass',
            role=UserChoice.MANAGER,
            is_verified=True,
            email='manager@example.com',     # MUST be unique
            phone='998000000002',            # 12 digits for phone, also unique
            balance=0
        )

        # DRF router base for PaymentViewSet, e.g. /payments/
        # If your router uses a different basename or path, adjust accordingly.
        # Typically, if you did: router.register(r'', PaymentViewSet)
        #   the list endpoint might be named 'paymentmodel-list' or 'payment-list'.
        self.payment_list_url = reverse('paymentmodel-list')

    def authenticate(self, user):
        """
        Helper method to authenticate a user with JWT tokens.
        """
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_create_payment_as_client(self):
        """
        Client should be able to create a payment (top-up).
        """
        self.authenticate(self.client_user)
        data = {
            'amount': '100.00',
            'card_number': '1234567812345678',  # 16 digits
            'expiry_date': '12/25',            # MM/YY
            'cvv': '123'
        }

        response = self.client.post(self.payment_list_url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn('id', response.data)
        self.assertIn('transaction_id', response.data)
        self.assertEqual(response.data['status'], PaymentStatusChoices.COMPLETED)

        # Verify the client's balance has been updated
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.balance, 100.00)

        # Verify the PaymentModel record
        payment_id = response.data['id']
        payment = PaymentModel.objects.get(id=payment_id)
        self.assertEqual(payment.user, self.client_user)
        self.assertEqual(payment.amount, 100.00)
        self.assertEqual(payment.status, PaymentStatusChoices.COMPLETED)

    def test_create_payment_unauthenticated(self):
        """
        Unauthenticated user should not be allowed to create a payment.
        """
        data = {
            'amount': '50.00',
            'card_number': '1111222233334444',
            'expiry_date': '11/24',
            'cvv': '999'
        }
        response = self.client.post(self.payment_list_url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_payments_as_client(self):
        """
        Client can only see their own payments.
        """
        # Create a payment for the client
        PaymentModel.objects.create(
            user=self.client_user,
            amount=80.00,
            status=PaymentStatusChoices.COMPLETED
        )
        # Create a payment for the manager
        PaymentModel.objects.create(
            user=self.manager_user,
            amount=150.00,
            status=PaymentStatusChoices.COMPLETED
        )

        self.authenticate(self.client_user)
        response = self.client.get(self.payment_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Client should only see 1 payment (their own)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['amount']), 80.00)

    def test_list_payments_as_manager(self):
        """
        Manager can see all payments.
        """
        PaymentModel.objects.create(
            user=self.client_user,
            amount=80.00,
            status=PaymentStatusChoices.COMPLETED
        )
        PaymentModel.objects.create(
            user=self.manager_user,
            amount=150.00,
            status=PaymentStatusChoices.COMPLETED
        )

        self.authenticate(self.manager_user)
        response = self.client.get(self.payment_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Manager should see both payments
        self.assertEqual(len(response.data), 2)

    def test_invalid_card_details(self):
        """
        Test invalid card number/expiry/cvv validations.
        """
        self.authenticate(self.client_user)
        invalid_data = {
            'amount': '50.00',
            'card_number': 'abcd567812345678',  # Not all digits
            'expiry_date': '13/25',            # Invalid month
            'cvv': '12'                        # Too short
        }

        response = self.client.post(self.payment_list_url, data=invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('card_number', response.data)
        self.assertIn('expiry_date', response.data)
        self.assertIn('cvv', response.data)
