from datetime import date

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from resy_bot.errors import NoSlotsError
from resy_bot.models import ResolvedVenue
from tests.factories import (
    ReservationRequestFactory,
    SlotFactory,
    TimedReservationRequestFactory,
)


client = TestClient(app)


def setup_function():
    main_module.job_store.clear()
    main_module.cancellation_events.clear()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_slots(monkeypatch):
    slot = SlotFactory.create()
    request = ReservationRequestFactory.create()

    monkeypatch.setattr(
        main_module.reservation_service,
        "check_slots_with_venue",
        lambda _: ([slot], ResolvedVenue(venue_id="9802", name="Test Venue")),
    )

    response = client.post("/slots", json=request.model_dump(mode="json"))

    assert response.status_code == 200
    assert response.json()["venue"]["name"] == "Test Venue"
    assert response.json()["slots"][0]["config"]["token"] == slot.config.token


def test_slots_maps_no_slots(monkeypatch):
    request = ReservationRequestFactory.create()

    def raise_no_slots(_):
        raise NoSlotsError("No slots found")

    monkeypatch.setattr(
        main_module.reservation_service,
        "check_slots_with_venue",
        raise_no_slots,
    )

    response = client.post("/slots", json=request.model_dump(mode="json"))

    assert response.status_code == 404
    assert response.json() == {"detail": "No slots found"}


def test_reserve_creates_job(monkeypatch):
    request = TimedReservationRequestFactory.create(
        expected_drop_hour=10,
        expected_drop_minute=0,
        reservation_request=ReservationRequestFactory.create(
            venue_name="Carbone",
            venue_location="New York",
            party_size=4,
            ideal_date=date(2026, 7, 15),
            ideal_hour=19,
            ideal_minute=30,
            window_hours=1,
            preferred_type="Dining Room",
        ),
    )

    monkeypatch.setattr(
        main_module.reservation_service,
        "reserve",
        lambda *_, **__: "reservation-token",
    )

    response = client.post("/reserve", json=request.model_dump(mode="json"))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"

    job_response = client.get(f"/jobs/{body['job_id']}")

    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "succeeded"
    assert job["reservation_token"] == "reservation-token"
    assert job["reservation"] == {
        "restaurant_name": "Carbone",
        "venue_id": request.reservation_request.venue_id,
        "venue_location": "New York",
        "party_size": 4,
        "ideal_date": "2026-07-15",
        "days_in_advance": None,
        "ideal_time": "7:30 PM",
        "window_hours": 1,
        "prefer_early": request.reservation_request.prefer_early,
        "preferred_type": "Dining Room",
        "method": "scheduled",
        "expected_drop_time": "10:00 AM",
    }


def test_reserve_persists_job(monkeypatch):
    request = TimedReservationRequestFactory.create()

    monkeypatch.setattr(
        main_module.reservation_service,
        "reserve",
        lambda *_, **__: "reservation-token",
    )

    response = client.post("/reserve", json=request.model_dump(mode="json"))

    assert response.status_code == 202
    stored_job = main_module.job_store.get_job(response.json()["job_id"])
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert stored_job.reservation_token == "reservation-token"


def test_list_jobs(monkeypatch):
    request = TimedReservationRequestFactory.create()

    monkeypatch.setattr(
        main_module.reservation_service,
        "reserve",
        lambda *_, **__: "reservation-token",
    )

    response = client.post("/reserve", json=request.model_dump(mode="json"))

    assert response.status_code == 202

    jobs_response = client.get("/jobs")

    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == response.json()["job_id"]
    assert jobs[0]["status"] == "succeeded"
    assert jobs[0]["reservation_token"] == "reservation-token"
    assert jobs[0]["reservation"]["party_size"] == request.reservation_request.party_size


def test_get_job_not_found():
    response = client.get("/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
