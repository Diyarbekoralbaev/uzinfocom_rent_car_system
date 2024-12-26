from django.urls import path
from .views import RegisterView, VerifyView, LoginView, ChangePasswordView, ResetPasswordView, ResetPasswordConfirmView, UserView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),

    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('reset-password-confirm/', ResetPasswordConfirmView.as_view(), name='reset-password-confirm'),
    path('me/', UserView.as_view(), name='me'),
]