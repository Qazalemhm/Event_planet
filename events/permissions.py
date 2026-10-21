from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOrganizer(BasePermission):
    message = "Organizer role is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "organizer")


class IsParticipant(BasePermission):
    message = "Participant role is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "participant")


class IsEventOrganizer(BasePermission):
    message = "Only the organizer who owns this event may perform this action."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        event = obj if hasattr(obj, "organizer_id") else getattr(obj, "event", None)
        return bool(event and request.user.is_authenticated and event.organizer_id == request.user.id)


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "participant", None) or getattr(obj, "user", None)
        return bool(request.user.is_authenticated and owner == request.user)
