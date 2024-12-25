from rest_framework.permissions import BasePermission, SAFE_METHODS
from users.models import UserChoice
class IsManager(BasePermission):
    """
    Allows access only to manager users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserChoice.MANAGER

class IsAuthenticatedClientOrManager(BasePermission):
    """
    Allows access to authenticated clients (read-only) and managers (full access).
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            if request.user.role == UserChoice.MANAGER:
                return True
            elif request.user.role == UserChoice.CLIENT:
                return request.method in SAFE_METHODS
        return False
