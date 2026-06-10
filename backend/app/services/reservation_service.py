import time
from os import environ
from threading import Event

from app.env import load_backend_env
from resy_bot.errors import ReservationCancelledError
from resy_bot.logging_config import logging
from resy_bot.manager import ResyManager
from resy_bot.models import (
    BookingMethod,
    ReservationRequest,
    ResyConfig,
    TimedReservationRequest,
)


load_backend_env()

REQUIRED_RESY_ENV_VARS = (
    "RESY_API_KEY",
    "RESY_TOKEN",
    "RESY_PAYMENT_METHOD_ID",
    "RESY_EMAIL",
    "RESY_PASSWORD",
)


def load_resy_config() -> ResyConfig:
    missing = [key for key in REQUIRED_RESY_ENV_VARS if not environ.get(key)]

    if missing:
        raise ValueError(f"Missing Resy environment variables: {', '.join(missing)}")

    return ResyConfig(
        api_key=environ["RESY_API_KEY"],
        token=environ["RESY_TOKEN"],
        payment_method_id=int(environ["RESY_PAYMENT_METHOD_ID"]),
        email=environ["RESY_EMAIL"],
        password=environ["RESY_PASSWORD"],
    )


def check_slots(reservation_request: dict) -> list:
    config = load_resy_config()
    manager = ResyManager.build(config)
    request = ReservationRequest(**reservation_request)

    return manager.checkSlots(request)


def reserve(
    reservation_request: dict,
    resy_config: dict | None = None,
    /,
    cancel_event: Event | None = None,
) -> str:
    if resy_config and "api_key" in reservation_request:
        reservation_request, resy_config = resy_config, reservation_request

    config = ResyConfig(**resy_config) if resy_config else load_resy_config()
    manager = ResyManager.build(config)
    request = TimedReservationRequest(**reservation_request)

    if request.reservation_request.method == BookingMethod.SCHEDULED:
        return timed_reserve(manager, request, cancel_event)
    elif request.reservation_request.method == BookingMethod.MONITOR:
        return monitor_reserve(manager, request.reservation_request, cancel_event)

    raise ValueError(
        f"Unsupported booking method: {request.reservation_request.method}"
    )


def timed_reserve(
    manager: ResyManager,
    timed_request: TimedReservationRequest,
    cancel_event: Event | None = None,
) -> str:
    return manager.make_reservation_at_opening_time(timed_request, cancel_event)


def monitor_reserve(
    manager: ResyManager,
    request: ReservationRequest,
    cancel_event: Event | None = None,
) -> str:
    slots = []
    while not slots:
        if cancel_event and cancel_event.is_set():
            raise ReservationCancelledError("Reservation job was cancelled")

        slots = manager.checkSlots(request)
        if slots:
            break

        if cancel_event:
            cancel_event.wait(5)
        else:
            time.sleep(5)

    return manager.make_reservation_with_retries(request, cancel_event)
