from uuid import uuid4

from django.core.cache import cache
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserModel, UserChoice
from .serializers import UserSerializer, LoginSerializer, VerifySerializer, ChangePasswordSerializer, \
    ResetPasswordSerializer, ResetPasswordConfirmSerializer, \
    TopUpSerializer
from .utils import generate_otp, send_sms_otp


class RegisterView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Register a new user',
        operation_summary='Register a new user',
        operation_description='Register a new user or resend verification for unverified users',
        request_body=UserSerializer,
        responses={
            201: UserSerializer(),
        }
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        verification_id = uuid4()

        # Check if user exists but is unverified
        existing_user = UserModel.objects.filter(
            username=request.data.get('username'),
            is_verified=False
        ).first()

        if existing_user:
            # Generate new OTP for existing unverified user
            otp = generate_otp()
            cache.set(verification_id, {
                'otp': otp,
                'user_id': existing_user.id,
            }, timeout=300)
            try:
                send_sms_otp(existing_user.phone, otp)
            except:
                pass # Ignore if SMS sending fails
            return Response({
                'verification_id': verification_id,
                'otp': otp,
                'data': UserSerializer(existing_user).data,
            }, status=status.HTTP_201_CREATED)

        if serializer.is_valid():
            otp = generate_otp()
            user = serializer.save(is_verified=False)
            cache.set(verification_id, {
                'otp': otp,
                'user_id': user.id,
            }, timeout=300)
            try:
                send_sms_otp(user.phone, otp)
            except:
                pass # Ignore if SMS sending fails
            return Response({
                'verification_id': verification_id,
                'otp': otp,
                'data': serializer.data,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Verify a user',
        operation_summary='Verify a user',
        operation_description='Verify a user with the provided OTP and verification ID',
        request_body=VerifySerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
        }
    )
    def post(self, request):
        serializer = VerifySerializer(data=request.data)
        if serializer.is_valid():
            verification_id = serializer.validated_data['verification_id']
            otp = serializer.validated_data['code']
            data = cache.get(verification_id)
            if data is None:
                return Response({'message': 'Invalid verification ID'}, status=status.HTTP_400_BAD_REQUEST)
            if int(data['otp']) != int(otp):
                return Response({'message': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
            user = UserModel.objects.get(id=data['user_id'])
            user.is_verified = True
            user.save()
            cache.delete(verification_id)
            return Response({'message': 'User verified successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Login',
        operation_summary='Login',
        operation_description='Login with the provided username and password',
        request_body=LoginSerializer,
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                'access': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )}
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Change password',
        operation_summary='Change password',
        operation_description='Change the password of the authenticated user',
        request_body=ChangePasswordSerializer,
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )}
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'message': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Reset password',
        operation_summary='Reset password',
        operation_description='Reset the password of the user with the provided username',
        request_body=ResetPasswordSerializer,
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )}
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = UserModel.objects.filter(username=serializer.validated_data['username']).first()
            if user is None:
                return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            verification_id = uuid4()
            otp = generate_otp()
            cache.set(verification_id, {
                'otp': otp,
                'user_id': user.id,
            }, timeout=300)
            try:
                send_sms_otp(user.phone, otp)
            except:
                pass # Ignore if SMS sending fails
            return Response({
                'verification_id': verification_id,
                'otp': otp,
                'message': 'OTP sent successfully',
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Reset password confirm',
        operation_summary='Reset password confirm',
        operation_description='Confirm the OTP and reset the password of the user',
        request_body=ResetPasswordConfirmSerializer,
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )}
    )
    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        if serializer.is_valid():
            verification_id = serializer.validated_data['verification_id']
            otp = serializer.validated_data['code']
            data = cache.get(verification_id)
            if data is None:
                return Response({'message': 'Invalid verification ID'}, status=status.HTTP_400_BAD_REQUEST)
            if int(data['otp']) != int(otp):
                return Response({'message': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
            user = UserModel.objects.get(id=data['user_id'])
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            cache.delete(verification_id)
            return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TopUpView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Top up balance',
        operation_summary='Top up balance',
        operation_description='Top up the balance of the authenticated user',
        request_body=TopUpSerializer,
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )}
    )
    def post(self, request):
        serializer = TopUpSerializer(data=request.data)
        if serializer.is_valid():
            if request.user.role == UserChoice.MANAGER:
                user = UserModel.objects.get(id=serializer.validated_data['user_id'])
                user.balance += serializer.validated_data['amount']
                user.save()
                return Response({'message': 'Balance topped up successfully'}, status=status.HTTP_200_OK)
            return Response({'message': 'You do not have permission to top up the balance'},
                            status=status.HTTP_403_FORBIDDEN)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Users'],
        operation_id='Get user details',
        operation_summary='Get user details',
        operation_description='Get the details of the authenticated user',
        responses={200: UserSerializer()}
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)