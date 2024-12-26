# common/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from users.models import UserChoice
class IsManager(BasePermission):
    """
    Allows access only to users with the MANAGER role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserChoice.MANAGER

class IsClient(BasePermission):
    """
    Allows access only to users with the CLIENT role.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == UserChoice.CLIENT:
            return True
        if request.user.role == UserChoice.MANAGER and request.method in SAFE_METHODS:
            return True
        return False

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


class IsRentalOwnerOrManager(BasePermission):
    """
    Custom permission for RentalModel.
    - Manager: can do any request
    - Client: can read (GET, HEAD, OPTIONS) or create (POST) any rental,
              can PATCH/PUT/DELETE only their own rental
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        # Managers have full access
        if user.role == UserChoice.MANAGER:
            return True

        # Clients can read or create
        if user.role == UserChoice.CLIENT:
            if request.method in SAFE_METHODS:  # GET, HEAD, OPTIONS
                return True
            if request.method == 'POST':        # create
                return True
            # For PATCH/PUT/DELETE, must pass the object-level check
            if request.method in ['PATCH', 'PUT', 'DELETE']:
                return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Managers => can do anything
        if user.role == UserChoice.MANAGER:
            return True

        # Clients => must be the owner of the rental
        if user.role == UserChoice.CLIENT:
            return obj.client == user

        return False


class IsReservationOwnerOrManager(BasePermission):
    """
    Custom permission for ReservationModel.
    - Manager: can do any request
    - Client: can read (GET, HEAD, OPTIONS) or create (POST) any reservation,
              can PATCH/PUT/DELETE only their own reservation
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        if user.role == UserChoice.MANAGER:
            return True

        if user.role == UserChoice.CLIENT:
            if request.method in SAFE_METHODS:
                return True
            if request.method == 'POST':
                return True
            if request.method in ['PATCH', 'PUT', 'DELETE']:
                return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == UserChoice.MANAGER:
            return True

        if user.role == UserChoice.CLIENT:
            return obj.client == user

        return False