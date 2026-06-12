from datetime import date
from unittest.mock import MagicMock, call

from fastapi.testclient import TestClient

import app.main as main_module
import app.services.reservation_service as reservation_service
from app.main import app
from resy_bot.errors import NoSlotsError
from resy_bot.models import ResolvedVenue
from tests.factories import (
    MonitorReservationRequestFactory,
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
        "resolve_timed_reservation_request",
        lambda _: request,
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
        "monitor_dates": None,
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
        "resolve_timed_reservation_request",
        lambda _: request,
    )
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
        "resolve_timed_reservation_request",
        lambda _: request,
    )
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


def test_reserve_stores_resolved_venue_details(monkeypatch):
    request = TimedReservationRequestFactory.create(
        reservation_request=ReservationRequestFactory.create(
            venue_id=None,
            venue_name="user typed name",
            venue_location="nyc",
        ),
    )
    resolved_request = request.model_copy(
        update={
            "reservation_request": request.reservation_request.model_copy(
                update={
                    "venue_id": "9802",
                    "venue_name": "Carbone",
                    "venue_location": "New York",
                }
            )
        }
    )
    captured = {}

    monkeypatch.setattr(
        main_module.reservation_service,
        "resolve_timed_reservation_request",
        lambda _: resolved_request,
    )

    def reserve_resolved(reservation_request, *_, **__):
        captured["request"] = reservation_request
        return "reservation-token"

    monkeypatch.setattr(
        main_module.reservation_service,
        "reserve",
        reserve_resolved,
    )

    response = client.post("/reserve", json=request.model_dump(mode="json"))

    assert response.status_code == 202
    job = client.get(f"/jobs/{response.json()['job_id']}").json()
    assert job["reservation"]["restaurant_name"] == "Carbone"
    assert job["reservation"]["venue_id"] == "9802"
    assert job["reservation"]["venue_location"] == "New York"
    assert captured["request"]["reservation_request"]["venue_name"] == "Carbone"
    assert captured["request"]["reservation_request"]["venue_id"] == "9802"


def test_slots_returns_monitor_slots_by_date(monkeypatch):
    first_slot = SlotFactory.create()
    second_slot = SlotFactory.create()
    request = MonitorReservationRequestFactory.create(
        monitor_dates=[date(2026, 7, 1), date(2026, 7, 2)],
    )

    monkeypatch.setattr(
        main_module.reservation_service,
        "check_slots_with_venue",
        lambda _: (
            [first_slot, second_slot],
            ResolvedVenue(venue_id="9802", name="Test Venue"),
            {
                "2026-07-01": [first_slot],
                "2026-07-02": [second_slot],
            },
        ),
    )

    response = client.post("/slots", json=request.model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["venue"]["name"] == "Test Venue"
    assert body["slots_by_date"]["2026-07-01"][0]["config"]["token"] == first_slot.config.token
    assert body["slots_by_date"]["2026-07-02"][0]["config"]["token"] == second_slot.config.token


def test_monitor_reserve_books_first_acceptable_date():
    request = MonitorReservationRequestFactory.create(
        monitor_dates=[date(2026, 7, 1), date(2026, 7, 2)],
    )
    manager = MagicMock()
    manager.make_reservation.side_effect = [NoSlotsError("No acceptable slots found"), "token"]

    token = reservation_service.monitor_reserve(manager, request)

    assert token == "token"
    assert manager.make_reservation.call_args_list == [
        call(request, date(2026, 7, 1)),
        call(request, date(2026, 7, 2)),
    ]


def test_get_job_not_found():
    response = client.get("/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
