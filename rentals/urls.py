from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RentalViewSet, ReservationViewSet

router = DefaultRouter()
router.register(r'reservations', ReservationViewSet)
router.register(r'', RentalViewSet)

urlpatterns = [
    path('', include(router.urls)),
]