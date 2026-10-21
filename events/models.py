import math

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class User(AbstractUser):
    ROLE_PARTICIPANT = "participant"
    ROLE_ORGANIZER = "organizer"
    ROLE_CHOICES = [
        (ROLE_PARTICIPANT, "Participant"),
        (ROLE_ORGANIZER, "Organizer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PARTICIPANT)
    groups = models.ManyToManyField(
        Group, blank=True, help_text="The groups this user belongs to.",
        related_name="custom_user_set", related_query_name="custom_user", verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission, blank=True, help_text="Specific permissions for this user.",
        related_name="custom_user_permissions_set", related_query_name="custom_user_permission",
        verbose_name="user permissions",
    )

    def __str__(self):
        return f"{self.username} ({self.role})"


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CLOSED = "closed", "Closed"
        FINISHED = "finished", "Finished"

    ALLOWED_TRANSITIONS = {
        Status.DRAFT: {Status.PUBLISHED},
        Status.PUBLISHED: {Status.CLOSED},
        Status.CLOSED: {Status.FINISHED},
        Status.FINISHED: set(),
    }

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_events",
        limit_choices_to={"role": "organizer"},
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time", "id"]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": "End time must be after start time."})
        if self.organizer_id and getattr(self.organizer, "role", None) != User.ROLE_ORGANIZER:
            raise ValidationError({"organizer": "Only an organizer account can own an event."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Stage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="stages")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["event", "order"], name="unique_stage_order_per_event")]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": "Stage end time must be after start time."})
        if self.event_id and self.start_time and self.end_time:
            if self.start_time < self.event.start_time or self.end_time > self.event.end_time:
                raise ValidationError("A stage must fit within its event's time range.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event.title} - {self.title}"


class DynamicAttribute(models.Model):
    class DataType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        BOOLEAN = "boolean", "Boolean"
        CHOICE = "choice", "Choice"

    name = models.CharField(max_length=100, unique=True)
    data_type = models.CharField(max_length=20, choices=DataType.choices, default=DataType.TEXT)
    choices = models.TextField(blank=True, help_text="For choice attributes, enter comma-separated allowed values.")

    def clean(self):
        super().clean()
        if self.data_type == self.DataType.CHOICE and not self.choices.strip():
            raise ValidationError({"choices": "Choice attributes must define allowed choices."})

    def __str__(self):
        return f"{self.name} ({self.data_type})"


class EventAttributeValue(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attribute_values")
    attribute = models.ForeignKey(DynamicAttribute, on_delete=models.CASCADE, related_name="event_values")
    value = models.TextField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "attribute"], name="unique_attribute_value_per_event")]

    def clean(self):
        super().clean()
        if not self.attribute_id:
            return
        data_type = self.attribute.data_type
        raw = self.value.strip()
        if data_type == DynamicAttribute.DataType.NUMBER:
            try:
                number = float(raw)
                if not math.isfinite(number):
                    raise ValueError
            except (TypeError, ValueError, OverflowError):
                raise ValidationError({"value": "This attribute requires a finite numeric value."})
        elif data_type == DynamicAttribute.DataType.BOOLEAN and raw.lower() not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValidationError({"value": "This attribute requires a boolean value."})
        elif data_type == DynamicAttribute.DataType.CHOICE:
            allowed = {choice.strip() for choice in self.attribute.choices.split(",") if choice.strip()}
            if raw not in allowed:
                raise ValidationError({"value": f"Choose one of: {', '.join(sorted(allowed))}."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event.title}: {self.attribute.name}={self.value}"


class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registrations")
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registered_at"]
        constraints = [models.UniqueConstraint(fields=["event", "participant"], name="unique_event_participant")]

    def __str__(self):
        return f"{self.participant.username} - {self.event.title}"


class Feedback(models.Model):
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.registration.event.title} ({self.rating}/5)"


class Result(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="results")
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_results")
    score = models.DecimalField(max_digits=10, decimal_places=2)
    details = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "participant"], name="unique_result_per_participant_event")]
        ordering = ["-score", "participant_id"]

    def __str__(self):
        return f"{self.event.title}: {self.participant.username} - {self.score}"
