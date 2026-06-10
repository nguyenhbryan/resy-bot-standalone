from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from resy_bot.errors import NoSlotsError
from tests.factories import ReservationRequestFactory, SlotFactory, TimedReservationRequestFactory


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
        "check_slots",
        lambda _: [slot],
    )

    response = client.post("/slots", json=request.model_dump(mode="json"))

    assert response.status_code == 200
    assert response.json()["slots"][0]["config"]["token"] == slot.config.token


def test_slots_maps_no_slots(monkeypatch):
    request = ReservationRequestFactory.create()

    def raise_no_slots(_):
        raise NoSlotsError("No slots found")

    monkeypatch.setattr(main_module.reservation_service, "check_slots", raise_no_slots)

    response = client.post("/slots", json=request.model_dump(mode="json"))

    assert response.status_code == 404
    assert response.json() == {"detail": "No slots found"}


def test_reserve_creates_job(monkeypatch):
    request = TimedReservationRequestFactory.create()

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
    assert job_response.json()["status"] == "succeeded"
    assert job_response.json()["reservation_token"] == "reservation-token"


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


def test_get_job_not_found():
    response = client.get("/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
