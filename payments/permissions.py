from rest_framework.permissions import BasePermission, SAFE_METHODS

from users.models import UserChoice


class IsManager(BasePermission):
    """
    Allows access only to users with the MANAGER role.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserChoice.MANAGER


class IsOwnerOrManager(BasePermission):
    """
    Allows access to owners of the object or managers.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserChoice.MANAGER:
            return True
        return obj.user == request.user


class IsAuthenticatedClientOrManager(BasePermission):
    """
    Allows full access to managers and read-only access to clients.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == UserChoice.MANAGER:
            return True
        if request.user.role == UserChoice.CLIENT and request.method in SAFE_METHODS:
            return True
        return False
