import time

from resy_bot.logging_config import logging
from resy_bot.manager import ResyManager
from resy_bot.models import (
    BookingMethod,
    ReservationRequest,
    ResyConfig,
    TimedReservationRequest,
)


def reserve(resy_config: dict, reservation_request: dict) -> str:
    config = ResyConfig(**resy_config)
    manager = ResyManager.build(config)
    request = TimedReservationRequest(**reservation_request)

    if request.reservation_request.method == BookingMethod.SCHEDULED:
        return timed_reserve(manager, request)
    elif request.reservation_request.method == BookingMethod.MONITOR:
        return monitor_reserve(manager, request.reservation_request)

    raise ValueError(
        f"Unsupported booking method: {request.reservation_request.method}"
    )


def timed_reserve(manager: ResyManager, timed_request: TimedReservationRequest) -> str:
    return manager.make_reservation_at_opening_time(timed_request)


def monitor_reserve(manager: ResyManager, request: ReservationRequest) -> str:
    slots = []
    while not slots:
        slots = manager.checkSlots(request)
        time.sleep(5)
    return manager.make_reservation_with_retries(request)
