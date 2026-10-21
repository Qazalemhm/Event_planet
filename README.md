# EVENT PLANET

API-first event planning platform built with Django REST Framework, PostgreSQL, and Docker. A lightweight Persian RTL UI is included as an optional API client.

## Architecture decisions

- Registrations are for the **whole event**, not individual stages. Capacity is enforced at event level. Stages have independent ordered schedules that must fit within the event's date range.
- `DynamicAttribute` stores reusable attribute metadata independently. `EventAttributeValue` stores one typed-as-text value per attribute per event. `JSONField` is not used; number, boolean, and choice values are validated in the API.
- Public event endpoints expose only `published` events. Organizers can see their own events, including drafts, and can only manage their own events.
- Event lifecycle transitions are `draft -> published -> closed -> finished`. Other transitions are rejected.
- Public results are shown only for `finished` events and only when `is_published=True`.
- New public sign-ups are participants. Organizer accounts should be created by an administrator using Django admin; the public registration endpoint ignores a submitted `role` field to prevent privilege escalation.

## Run with Docker

1. Copy `.env.example` to `.env` and set a long random `SECRET_KEY` and a strong local `DB_PASSWORD`.
2. Run `docker compose up --build -d` from this directory.
3. Open `http://localhost:8000/` for the optional UI or `http://localhost:8000/admin/` for Django admin.
4. Create an admin account: `docker compose exec web python manage.py createsuperuser`.
5. Create organizer accounts in Django admin by changing a user's role to `organizer`, or create one through Django shell for local testing.
6. API checks: `docker compose exec web python manage.py check` and `docker compose exec web python manage.py test`.

Migrations run automatically when the web container starts. Do not run `makemigrations` as a routine startup step; migration files are version-controlled.

## Environment variables

`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` are read from environment variables. `.env` is intentionally excluded from the Docker build context and Git.

## Main API endpoints

- `POST /api/register/`, `POST /api/login/`
- `GET /api/events/`, `POST /api/events/`, `GET/PATCH/DELETE /api/events/<id>/`
- `GET/POST /api/events/<event_id>/stages/`, `GET/PATCH/DELETE /api/stages/<id>/`
- `GET/POST /api/attributes/`, `GET/PATCH/DELETE /api/attributes/<id>/`, `GET/POST /api/events/<event_id>/attributes/`, `GET/PATCH/DELETE /api/event-attribute-values/<id>/`
- `GET/POST /api/registrations/`, `GET /api/events/<event_id>/participants/`
- `GET/POST /api/feedback/`, `GET/POST /api/results/`

Protected endpoints use `Authorization: Token <token>`. Event creation requires an organizer token. Registration creation requires a participant token and accepts `{ "event": <event_id> }`. Feedback creation accepts `{ "registration": <registration_id>, "rating": 1-5, "comment": "..." }`. Result creation accepts `{ "event": <event_id>, "participant": <participant_id>, "score": "90.00", "details": "...", "is_published": true }` and requires a finished event and an enrolled participant.

## Existing database warning

This repository includes a clean initial migration intended for a **fresh database** because the original migration history did not match the original models. If you already have valuable data in a PostgreSQL volume created from the older schema, back it up and migrate it deliberately; do not delete the volume or overwrite a production database blindly. The old local SQLite database is not used by this PostgreSQL configuration.
