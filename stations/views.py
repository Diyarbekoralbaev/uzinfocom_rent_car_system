from django.views.decorators.gzip import gzip_page
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from rest_framework.response import Response

from .models import StationModel
from users.models import UserChoice
from .serializers import StationSerializer

@method_decorator(gzip_page, name='dispatch')
class StationViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing station instances.
    """
    serializer_class = StationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Overriding the default `get_queryset` to handle filtering based on user role.
        """
        if self.request.user.role == UserChoice.MANAGER:
            return StationModel.objects.all()
        return StationModel.objects.filter(is_active=True).order_by('name')

    def create(self, request, *args, **kwargs):
        """
        Overriding the default `create` method to handle setting the station manager.
        """
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().create(request, *args, **kwargs)
        return Response({'error': 'Only managers can create stations.'}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        """
        Overriding the default `update` method to handle updating the station manager.
        """
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().update(request, *args, **kwargs)
        return Response({'error': 'Only managers can update stations.'}, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        """
        Overriding the default `partial_update` method to handle updating the station manager.
        """
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().partial_update(request, *args, **kwargs)
        return Response({'error': 'Only managers can update stations.'}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        """
        Overriding the default `destroy` method to handle deleting the station manager.
        """
        user = request.user
        if user.role == UserChoice.MANAGER:
            return super().destroy(request, *args, **kwargs)
        return Response({'error': 'Only managers can delete stations.'}, status=status.HTTP_403_FORBIDDEN)
