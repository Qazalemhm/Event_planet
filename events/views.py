from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User, Event, Stage, DynamicAttribute, EventAttributeValue, Registration, Feedback, Result
from .permissions import IsOrganizer, IsParticipant
from .serializers import (
    UserSerializer, EventSerializer, StageSerializer, DynamicAttributeSerializer,
    EventAttributeValueSerializer, RegistrationSerializer, FeedbackSerializer, ResultSerializer,
)


def home(request):
    return render(request, "index.html")


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class CustomObtainAuthToken(ObtainAuthToken):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.pk, "username": user.username, "email": user.email, "role": user.role})


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Event.objects.annotate(registered_count=Count("registrations")).select_related("organizer")
        if self.request.user.is_authenticated and self.request.user.role == User.ROLE_ORGANIZER:
            return qs.filter(Q(status=Event.Status.PUBLISHED) | Q(organizer=self.request.user)).distinct()
        return qs.filter(status=Event.Status.PUBLISHED)


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Event.objects.annotate(registered_count=Count("registrations")).select_related("organizer")
        if self.request.user.is_authenticated and self.request.user.role == User.ROLE_ORGANIZER:
            return qs.filter(Q(status=Event.Status.PUBLISHED) | Q(organizer=self.request.user)).distinct()
        return qs.filter(status=Event.Status.PUBLISHED)

    def perform_update(self, serializer):
        if serializer.instance.organizer_id != self.request.user.id:
            raise PermissionDenied("You can only edit your own events.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.organizer_id != self.request.user.id:
            raise PermissionDenied("You can only delete your own events.")
        instance.delete()


class StageListCreateView(generics.ListCreateAPIView):
    serializer_class = StageSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]

    def get_event(self):
        return get_object_or_404(Event, pk=self.kwargs["event_pk"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["event"] = self.get_event()
        return context

    def get_queryset(self):
        qs = Stage.objects.filter(event_id=self.kwargs["event_pk"]).select_related("event")
        user = self.request.user
        if user.is_authenticated and user.role == User.ROLE_ORGANIZER:
            return qs.filter(Q(event__status=Event.Status.PUBLISHED) | Q(event__organizer=user)).distinct()
        return qs.filter(event__status=Event.Status.PUBLISHED)

    def perform_create(self, serializer):
        event = self.get_event()
        if event.organizer_id != self.request.user.id:
            raise PermissionDenied("Only the event owner can manage its stages.")
        serializer.save(event=event)


class StageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StageSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Stage.objects.select_related("event")
        user = self.request.user
        if user.is_authenticated and user.role == User.ROLE_ORGANIZER:
            return qs.filter(Q(event__status=Event.Status.PUBLISHED) | Q(event__organizer=user)).distinct()
        return qs.filter(event__status=Event.Status.PUBLISHED)

    def perform_update(self, serializer):
        if serializer.instance.event.organizer_id != self.request.user.id:
            raise PermissionDenied("Only the event owner can manage its stages.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.event.organizer_id != self.request.user.id:
            raise PermissionDenied("Only the event owner can manage its stages.")
        instance.delete()


class AttributeListCreateView(generics.ListCreateAPIView):
    queryset = DynamicAttribute.objects.all().order_by("name")
    serializer_class = DynamicAttributeSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]


class AttributeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DynamicAttribute.objects.all()
    serializer_class = DynamicAttributeSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]


class EventAttributeValueListCreateView(generics.ListCreateAPIView):
    serializer_class = EventAttributeValueSerializer

    def get_event(self):
        return get_object_or_404(Event, pk=self.kwargs["event_pk"])

    def get_queryset(self):
        event = self.get_event()
        if event.status != Event.Status.PUBLISHED and (not self.request.user.is_authenticated or event.organizer_id != self.request.user.id):
            raise PermissionDenied("This event's attributes are not public.")
        return EventAttributeValue.objects.filter(event=event).select_related("attribute", "event")

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]

    def perform_create(self, serializer):
        event = self.get_event()
        if event.organizer_id != self.request.user.id:
            raise PermissionDenied("Only the event owner can set attribute values.")
        serializer.save(event=event)


class EventAttributeValueDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EventAttributeValueSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]

    def get_queryset(self):
        qs = EventAttributeValue.objects.select_related("event", "attribute")
        user = self.request.user
        if user.is_authenticated and user.role == User.ROLE_ORGANIZER:
            return qs.filter(Q(event__status=Event.Status.PUBLISHED) | Q(event__organizer=user)).distinct()
        return qs.filter(event__status=Event.Status.PUBLISHED)

    def perform_update(self, serializer):
        if serializer.instance.event.organizer_id != self.request.user.id:
            raise PermissionDenied("Only the event owner can change attribute values.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.event.organizer_id != self.request.user.id:
            raise PermissionDenied("Only the event owner can delete attribute values.")
        instance.delete()


class RegistrationListCreateView(generics.ListCreateAPIView):
    serializer_class = RegistrationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsParticipant()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.ROLE_PARTICIPANT:
            return Registration.objects.filter(participant=user).select_related("event", "participant")
        return Registration.objects.filter(event__organizer=user).select_related("event", "participant")

    def create(self, request, *args, **kwargs):
        event_id = request.data.get("event")
        if not event_id:
            raise ValidationError({"event": "This field is required."})
        try:
            with transaction.atomic():
                # Lock the event row so concurrent registrations for the same event
                # serialize before checking capacity.
                event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
                if event.status != Event.Status.PUBLISHED:
                    raise ValidationError({"event": "Only published events accept registrations."})
                if Registration.objects.filter(event=event, participant=request.user).exists():
                    raise ValidationError({"event": "You are already registered for this event."})
                if event.registrations.count() >= event.capacity:
                    raise ValidationError({"event": "This event has reached its capacity."})
                registration = Registration.objects.create(event=event, participant=request.user)
        except IntegrityError:
            # Catch outside atomic(): the transaction must be rolled back first.
            raise ValidationError({"event": "You are already registered for this event."})
        return Response(self.get_serializer(registration).data, status=status.HTTP_201_CREATED)


class EventParticipantsView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        event = get_object_or_404(Event, pk=self.kwargs["event_pk"], organizer=self.request.user)
        return Registration.objects.filter(event=event).select_related("event", "participant")


class FeedbackListCreateView(generics.ListCreateAPIView):
    serializer_class = FeedbackSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsParticipant()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.ROLE_ORGANIZER:
            return Feedback.objects.filter(registration__event__organizer=user).select_related("registration__event", "registration__participant")
        return Feedback.objects.filter(registration__participant=user).select_related("registration__event", "registration__participant")

    def create(self, request, *args, **kwargs):
        registration_id = request.data.get("registration")
        if not registration_id:
            raise ValidationError({"registration": "This field is required."})
        registration = get_object_or_404(Registration, pk=registration_id, participant=request.user)
        if registration.event.status != Event.Status.FINISHED:
            raise ValidationError({"registration": "Feedback is only allowed after the event is finished."})
        if hasattr(registration, "feedback"):
            raise ValidationError({"registration": "Feedback has already been submitted for this registration."})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save(registration=registration)
        return Response(self.get_serializer(feedback).data, status=status.HTTP_201_CREATED)


class ResultListCreateView(generics.ListCreateAPIView):
    serializer_class = ResultSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsOrganizer()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Result.objects.select_related("event", "participant").filter(event__status=Event.Status.FINISHED)
        if self.request.user.is_authenticated and self.request.user.role == User.ROLE_ORGANIZER:
            return qs.filter(event__organizer=self.request.user) | qs.filter(is_published=True)
        return qs.filter(is_published=True)

    def create(self, request, *args, **kwargs):
        event_id = request.data.get("event")
        participant_id = request.data.get("participant")
        event = get_object_or_404(Event, pk=event_id, organizer=request.user)
        if event.status != Event.Status.FINISHED:
            raise ValidationError({"event": "Results can only be added after the event is finished."})
        if not participant_id:
            raise ValidationError({"participant": "This field is required."})
        participant = get_object_or_404(User, pk=participant_id, role=User.ROLE_PARTICIPANT)
        if not Registration.objects.filter(event=event, participant=participant).exists():
            raise ValidationError({"participant": "The participant must be registered for this event."})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save(event=event, participant=participant)
        return Response(self.get_serializer(result).data, status=status.HTTP_201_CREATED)
