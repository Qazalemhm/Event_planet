import math

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User, Event, Stage, DynamicAttribute, EventAttributeValue, Registration, Feedback, Result


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role"]
        read_only_fields = ["role"]

    def create(self, validated_data):
        validated_data.pop("role", None)
        return User.objects.create_user(role=User.ROLE_PARTICIPANT, **validated_data)


class EventSerializer(serializers.ModelSerializer):
    organizer = serializers.PrimaryKeyRelatedField(read_only=True)
    organizer_username = serializers.CharField(source="organizer.username", read_only=True)
    registered_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = ["id", "title", "description", "organizer", "organizer_username", "start_time", "end_time", "capacity", "status", "created_at", "registered_count"]
        read_only_fields = ["id", "organizer", "created_at", "registered_count"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        if self.instance is None and attrs.get("status", Event.Status.DRAFT) != Event.Status.DRAFT:
            raise serializers.ValidationError({"status": "New events must start as draft. Publish them in a separate status transition."})
        if self.instance and "status" in attrs and attrs["status"] != self.instance.status:
            if attrs["status"] not in Event.ALLOWED_TRANSITIONS[self.instance.status]:
                raise serializers.ValidationError({"status": f"Invalid transition from {self.instance.status} to {attrs['status']}."})
        if self.instance and "capacity" in attrs and attrs["capacity"] < self.instance.registrations.count():
            raise serializers.ValidationError({"capacity": "Capacity cannot be lower than the current registration count."})
        return attrs

    def create(self, validated_data):
        validated_data["organizer"] = self.context["request"].user
        validated_data["status"] = Event.Status.DRAFT
        event = Event(**validated_data)
        try:
            event.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        event.save()
        return event

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()
        return instance


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ["id", "event", "title", "description", "order", "start_time", "end_time"]
        read_only_fields = ["id", "event"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "Stage end time must be after start time."})
        event = getattr(self.instance, "event", None) or self.context.get("event")
        if event and start and end and (start < event.start_time or end > event.end_time):
            raise serializers.ValidationError("A stage must fit within its event's time range.")
        return attrs


class DynamicAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicAttribute
        fields = ["id", "name", "data_type", "choices"]

    def validate(self, attrs):
        data_type = attrs.get("data_type", getattr(self.instance, "data_type", DynamicAttribute.DataType.TEXT))
        choices = attrs.get("choices", getattr(self.instance, "choices", ""))
        if data_type == DynamicAttribute.DataType.CHOICE and not choices.strip():
            raise serializers.ValidationError({"choices": "Choice attributes must define allowed choices, separated by commas."})
        return attrs


class EventAttributeValueSerializer(serializers.ModelSerializer):
    attribute_name = serializers.CharField(source="attribute.name", read_only=True)
    data_type = serializers.CharField(source="attribute.data_type", read_only=True)

    class Meta:
        model = EventAttributeValue
        fields = ["id", "event", "attribute", "attribute_name", "data_type", "value"]
        read_only_fields = ["id", "event"]

    def validate(self, attrs):
        attribute = attrs.get("attribute", getattr(self.instance, "attribute", None))
        value = attrs.get("value", getattr(self.instance, "value", ""))
        if not attribute:
            return attrs
        if self.instance is None:
            event = self.context.get("view").get_event() if self.context.get("view") and hasattr(self.context.get("view"), "get_event") else None
            if event and EventAttributeValue.objects.filter(event=event, attribute=attribute).exists():
                raise serializers.ValidationError({"attribute": "This attribute already has a value for this event."})
        data_type = attribute.data_type
        raw = str(value).strip()
        if data_type == DynamicAttribute.DataType.NUMBER:
            try:
                number = float(raw)
                if not math.isfinite(number):
                    raise ValueError
            except (TypeError, ValueError, OverflowError):
                raise serializers.ValidationError({"value": "This attribute requires a finite numeric value."})
        elif data_type == DynamicAttribute.DataType.BOOLEAN and raw.lower() not in {"true", "false", "1", "0", "yes", "no"}:
            raise serializers.ValidationError({"value": "This attribute requires a boolean value."})
        elif data_type == DynamicAttribute.DataType.CHOICE:
            allowed = {item.strip() for item in attribute.choices.split(",") if item.strip()}
            if raw not in allowed:
                raise serializers.ValidationError({"value": f"Choose one of: {', '.join(sorted(allowed))}."})
        return attrs


class RegistrationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)

    class Meta:
        model = Registration
        fields = ["id", "event", "event_title", "participant", "registered_at"]
        read_only_fields = ["id", "participant", "registered_at", "event_title"]


class FeedbackSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="registration.event.title", read_only=True)
    participant_username = serializers.CharField(source="registration.participant.username", read_only=True)

    class Meta:
        model = Feedback
        fields = ["id", "registration", "event_title", "participant_username", "rating", "comment", "created_at"]
        read_only_fields = ["id", "registration", "event_title", "participant_username", "created_at"]


class ResultSerializer(serializers.ModelSerializer):
    participant_username = serializers.CharField(source="participant.username", read_only=True)

    class Meta:
        model = Result
        fields = ["id", "event", "participant", "participant_username", "score", "details", "is_published"]
        read_only_fields = ["id", "participant_username"]
