from datetime import date

import pytest
from pydantic import ValidationError

from resy_bot.models import BookingMethod, ReservationRequest
from tests.factories import (
    MonitorReservationRequestFactory,
    ReservationRequestDaysInAdvanceFactory,
    ReservationRequestFactory,
)


def test_scheduled_accepts_ideal_date():
    request = ReservationRequestFactory.create(ideal_date=date(2026, 7, 1))

    assert request.target_dates == [date(2026, 7, 1)]


def test_scheduled_accepts_days_in_advance():
    request = ReservationRequestDaysInAdvanceFactory.create(days_in_advance=20)

    assert len(request.target_dates) == 1


def test_scheduled_rejects_date_and_days_in_advance():
    with pytest.raises(ValidationError, match="Must only provide one"):
        ReservationRequest(
            venue_id="123",
            party_size=2,
            ideal_date=date(2026, 7, 1),
            days_in_advance=20,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
            prefer_early=False,
            preferred_type=None,
            method=BookingMethod.SCHEDULED,
        )


def test_monitor_accepts_multiple_dates_and_preserves_order():
    request = MonitorReservationRequestFactory.create(
        monitor_dates=["2026-07-03", "2026-07-01", "2026-07-03"],
    )

    assert request.target_dates == [date(2026, 7, 3), date(2026, 7, 1)]


def test_monitor_rejects_days_in_advance():
    with pytest.raises(ValidationError, match="Monitor requests must use monitor_dates"):
        MonitorReservationRequestFactory.create(days_in_advance=20)


def test_monitor_uses_legacy_ideal_date_as_single_monitor_date():
    request = ReservationRequest(
        venue_id="123",
        party_size=2,
        ideal_date=date(2026, 7, 1),
        ideal_hour=19,
        ideal_minute=0,
        window_hours=1,
        prefer_early=False,
        preferred_type=None,
        method=BookingMethod.MONITOR,
    )

    assert request.target_dates == [date(2026, 7, 1)]
