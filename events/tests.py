from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from .models import User, Event, Registration, DynamicAttribute, EventAttributeValue


class EventPlanetAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="organizer", password="Strong-pass-123", role=User.ROLE_ORGANIZER)
        self.participant = User.objects.create_user(username="participant", password="Strong-pass-123", role=User.ROLE_PARTICIPANT)
        now = timezone.now()
        self.event = Event.objects.create(title="Public event", description="Test", organizer=self.organizer,
            start_time=now + timedelta(days=1), end_time=now + timedelta(days=1, hours=2), capacity=1,
            status=Event.Status.PUBLISHED)
        self.draft = Event.objects.create(title="Private draft", description="Test", organizer=self.organizer,
            start_time=now + timedelta(days=2), end_time=now + timedelta(days=2, hours=2), capacity=1,
            status=Event.Status.DRAFT)

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_public_event_list_only_shows_published(self):
        response = self.client.get("/api/events/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["title"] for row in response.data], ["Public event"])

    def test_registration_capacity_and_duplicate_are_enforced(self):
        self.authenticate(self.participant)
        first = self.client.post("/api/registrations/", {"event": self.event.id}, format="json")
        self.assertEqual(first.status_code, 201)
        duplicate = self.client.post("/api/registrations/", {"event": self.event.id}, format="json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Registration.objects.filter(event=self.event).count(), 1)

    def test_capacity_blocks_a_second_participant(self):
        another = User.objects.create_user(username="another", password="Strong-pass-123", role=User.ROLE_PARTICIPANT)
        self.authenticate(self.participant)
        first = self.client.post("/api/registrations/", {"event": self.event.id}, format="json")
        self.assertEqual(first.status_code, 201)
        self.authenticate(another)
        second = self.client.post("/api/registrations/", {"event": self.event.id}, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Registration.objects.filter(event=self.event).count(), 1)

    def test_participant_cannot_create_event_or_upgrade_role(self):
        self.authenticate(self.participant)
        now = timezone.now()
        response = self.client.post("/api/events/", {"title": "Nope", "description": "", "start_time": (now + timedelta(days=1)).isoformat(), "end_time": (now + timedelta(days=1, hours=1)).isoformat(), "capacity": 3}, format="json")
        self.assertEqual(response.status_code, 403)
        register = self.client.post("/api/register/", {"username": "sneaky", "email": "s@example.com", "password": "Strong-pass-123", "role": "organizer"}, format="json")
        self.assertEqual(register.status_code, 201)
        self.assertEqual(User.objects.get(username="sneaky").role, User.ROLE_PARTICIPANT)

    def test_event_cannot_skip_lifecycle_on_creation(self):
        self.authenticate(self.organizer)
        now = timezone.now()
        response = self.client.post("/api/events/", {
            "title": "Skip status", "description": "", "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=1)).isoformat(), "capacity": 5, "status": "published"
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_only_owner_can_edit_event_and_status_transition_is_enforced(self):
        self.authenticate(self.participant)
        denied = self.client.patch(f"/api/events/{self.event.id}/", {"title": "Changed"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.authenticate(self.organizer)
        invalid = self.client.patch(f"/api/events/{self.event.id}/", {"status": "finished"}, format="json")
        self.assertEqual(invalid.status_code, 400)
        valid = self.client.patch(f"/api/events/{self.event.id}/", {"status": "closed"}, format="json")
        self.assertEqual(valid.status_code, 200)

    def test_feedback_requires_finished_event_and_registration(self):
        self.authenticate(self.participant)
        reg = Registration.objects.create(event=self.event, participant=self.participant)
        early = self.client.post("/api/feedback/", {"registration": reg.id, "rating": 5, "comment": "Good"}, format="json")
        self.assertEqual(early.status_code, 400)
        self.event.status = Event.Status.FINISHED
        self.event.save()
        finished = self.client.post("/api/feedback/", {"registration": reg.id, "rating": 5, "comment": "Good"}, format="json")
        self.assertEqual(finished.status_code, 201)

    def test_result_creation_requires_finished_event_and_owner(self):
        self.authenticate(self.organizer)
        Registration.objects.create(event=self.event, participant=self.participant)
        payload = {"event": self.event.id, "participant": self.participant.id, "score": "92.50", "is_published": True}
        early = self.client.post("/api/results/", payload, format="json")
        self.assertEqual(early.status_code, 400)
        self.event.status = Event.Status.FINISHED
        self.event.save()
        done = self.client.post("/api/results/", payload, format="json")
        self.assertEqual(done.status_code, 201)
        public = self.client.get("/api/results/")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(len(public.data), 1)

    def test_dynamic_attribute_values_are_type_checked_and_shared_metadata(self):
        attr = DynamicAttribute.objects.create(name="Round count", data_type=DynamicAttribute.DataType.NUMBER)
        self.authenticate(self.organizer)
        bad = self.client.post(f"/api/events/{self.event.id}/attributes/", {"attribute": attr.id, "value": "many"}, format="json")
        self.assertEqual(bad.status_code, 400)
        good = self.client.post(f"/api/events/{self.event.id}/attributes/", {"attribute": attr.id, "value": "3"}, format="json")
        self.assertEqual(good.status_code, 201)

    def test_dynamic_numeric_attribute_rejects_nan_and_infinity(self):
        attr = DynamicAttribute.objects.create(name="Finite number", data_type=DynamicAttribute.DataType.NUMBER)
        self.authenticate(self.organizer)
        for invalid_value in ("NaN", "Infinity", "-Infinity", "inf", "-inf"):
            with self.subTest(value=invalid_value):
                response = self.client.post(
                    f"/api/events/{self.event.id}/attributes/",
                    {"attribute": attr.id, "value": invalid_value},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

    def test_stage_must_fit_inside_event_time_range(self):
        self.authenticate(self.organizer)
        outside_start = self.event.start_time - timedelta(hours=1)
        response = self.client.post(
            f"/api/events/{self.event.id}/stages/",
            {
                "title": "Outside stage",
                "description": "",
                "order": 1,
                "start_time": outside_start.isoformat(),
                "end_time": (self.event.start_time + timedelta(minutes=30)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_owner_cannot_manage_another_organizers_event(self):
        other_organizer = User.objects.create_user(
            username="other-organizer", password="Strong-pass-123", role=User.ROLE_ORGANIZER
        )
        self.authenticate(other_organizer)
        response = self.client.patch(
            f"/api/events/{self.event.id}/",
            {"title": "Unauthorized change"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Public event")

    def test_public_results_hide_unpublished_and_unfinished_results(self):
        Registration.objects.create(event=self.event, participant=self.participant)
        self.event.status = Event.Status.FINISHED
        self.event.save()
        self.authenticate(self.organizer)
        hidden = self.client.post(
            "/api/results/",
            {"event": self.event.id, "participant": self.participant.id, "score": "80.00", "is_published": False},
            format="json",
        )
        self.assertEqual(hidden.status_code, 201)
        self.client.credentials()  # Public request, no token.
        public_list = self.client.get("/api/results/")
        self.assertEqual(public_list.status_code, 200)
        self.assertEqual(len(public_list.data), 0)
