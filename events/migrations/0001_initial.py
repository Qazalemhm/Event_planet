# Initial schema for a fresh EVENT PLANET installation.
import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(name="DynamicAttribute", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=100, unique=True)),
            ("data_type", models.CharField(choices=[("text", "Text"), ("number", "Number"), ("boolean", "Boolean"), ("choice", "Choice")], default="text", max_length=20)),
            ("choices", models.TextField(blank=True, help_text="For choice attributes, enter comma-separated allowed values.")),
        ]),
        migrations.CreateModel(name="User", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("password", models.CharField(max_length=128, verbose_name="password")),
            ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
            ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
            ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name="username")),
            ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
            ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
            ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
            ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
            ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
            ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
            ("role", models.CharField(choices=[("participant", "Participant"), ("organizer", "Organizer")], default="participant", max_length=20)),
            ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to.", related_name="custom_user_set", related_query_name="custom_user", to="auth.group", verbose_name="groups")),
            ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="custom_user_permissions_set", related_query_name="custom_user_permission", to="auth.permission", verbose_name="user permissions")),
        ], options={"verbose_name": "user", "verbose_name_plural": "users", "abstract": False}, managers=[("objects", django.contrib.auth.models.UserManager())]),
        migrations.CreateModel(name="Event", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=255)), ("description", models.TextField(blank=True)),
            ("start_time", models.DateTimeField()), ("end_time", models.DateTimeField()),
            ("capacity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
            ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("closed", "Closed"), ("finished", "Finished")], default="draft", max_length=20)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organizer", models.ForeignKey(limit_choices_to={"role": "organizer"}, on_delete=django.db.models.deletion.CASCADE, related_name="organized_events", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["start_time", "id"]}),
        migrations.CreateModel(name="Stage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=255)), ("description", models.TextField(blank=True)),
            ("order", models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
            ("start_time", models.DateTimeField()), ("end_time", models.DateTimeField()),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stages", to="events.event")),
        ], options={"ordering": ["order", "id"]}),
        migrations.CreateModel(name="Registration", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("registered_at", models.DateTimeField(auto_now_add=True)),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="registrations", to="events.event")),
            ("participant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="registrations", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-registered_at"]}),
        migrations.CreateModel(name="EventAttributeValue", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("value", models.TextField()),
            ("attribute", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="event_values", to="events.dynamicattribute")),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attribute_values", to="events.event")),
        ]),
        migrations.CreateModel(name="Feedback", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("rating", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
            ("comment", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("registration", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="feedback", to="events.registration")),
        ]),
        migrations.CreateModel(name="Result", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("score", models.DecimalField(decimal_places=2, max_digits=10)), ("details", models.TextField(blank=True)),
            ("is_published", models.BooleanField(default=False)),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="events.event")),
            ("participant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="event_results", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-score", "participant_id"]}),
        migrations.AddConstraint(model_name="stage", constraint=models.UniqueConstraint(fields=("event", "order"), name="unique_stage_order_per_event")),
        migrations.AddConstraint(model_name="registration", constraint=models.UniqueConstraint(fields=("event", "participant"), name="unique_event_participant")),
        migrations.AddConstraint(model_name="eventattributevalue", constraint=models.UniqueConstraint(fields=("event", "attribute"), name="unique_attribute_value_per_event")),
        migrations.AddConstraint(model_name="result", constraint=models.UniqueConstraint(fields=("event", "participant"), name="unique_result_per_participant_event")),
    ]
