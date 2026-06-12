from datetime import UTC, datetime, timedelta
import pytest
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from resy_bot.errors import NoSlotsError, ExhaustedRetriesError
from resy_bot.api_access import ResyApiAccess
from resy_bot.models import (
    FindRequestBody,
    DetailsRequestBody,
    BookRequestBody,
    PaymentMethod,
    ReservationRetriesConfig,
)
from resy_bot.manager import ResyManager
from resy_bot.venue_resolver import VenueCache, VenueCandidate, VenueResolver

from tests.factories import (
    ResyConfigFactory,
    SlotFactory,
    ReservationRequestFactory,
    DetailsResponseBodyFactory,
    ReservationRetriesConfigFactory,
    TimedReservationRequestFactory,
    ReservationRequestDaysInAdvanceFactory,
)


def test_build():
    config = ResyConfigFactory.create()
    manager = ResyManager.build(config)

    assert isinstance(manager, ResyManager)
    assert isinstance(manager.api_access, ResyApiAccess)


def test_make_reservation():
    config = ResyConfigFactory.create()
    retries_config = ReservationRetriesConfigFactory.create()
    request = ReservationRequestFactory.create()
    mock_api_access = MagicMock()
    slots = SlotFactory.create_batch(3)
    mock_api_access.find_booking_slots.return_value = slots

    details_response = DetailsResponseBodyFactory.create()
    mock_api_access.get_booking_token.return_value = details_response

    mock_selector = MagicMock()
    mock_selector.select.return_value = slots[0]

    manager = ResyManager(config, mock_api_access, mock_selector, retries_config)

    manager.make_reservation(request)

    expected_day = request.ideal_date.strftime("%Y-%m-%d")

    expected_find_request_body = FindRequestBody(
        venue_id=request.venue_id, party_size=request.party_size, day=expected_day
    )

    expected_details_request_body = DetailsRequestBody(
        config_id=slots[0].config.token, day=expected_day, party_size=request.party_size
    )

    expected_booking_request = BookRequestBody(
        book_token=details_response.book_token.value,
        struct_payment_method=PaymentMethod(id=config.payment_method_id),
    )

    mock_api_access.find_booking_slots.assert_called_once_with(
        expected_find_request_body
    )

    mock_selector.select.assert_called_once_with(slots, request)

    mock_api_access.get_booking_token.assert_called_once_with(
        expected_details_request_body
    )

    mock_api_access.book_slot.assert_called_once_with(expected_booking_request)


def test_make_reservation_days_in_advance():
    config = ResyConfigFactory.create()
    retries_config = ReservationRetriesConfigFactory.create()
    request = ReservationRequestDaysInAdvanceFactory.create()
    mock_api_access = MagicMock()
    slots = SlotFactory.create_batch(3)
    mock_api_access.find_booking_slots.return_value = slots

    details_response = DetailsResponseBodyFactory.create()
    mock_api_access.get_booking_token.return_value = details_response

    mock_selector = MagicMock()
    mock_selector.select.return_value = slots[0]

    manager = ResyManager(config, mock_api_access, mock_selector, retries_config)

    manager.make_reservation(request)

    expected_day = request.target_date.strftime("%Y-%m-%d")

    expected_find_request_body = FindRequestBody(
        venue_id=request.venue_id, party_size=request.party_size, day=expected_day
    )

    expected_details_request_body = DetailsRequestBody(
        config_id=slots[0].config.token, day=expected_day, party_size=request.party_size
    )

    expected_booking_request = BookRequestBody(
        book_token=details_response.book_token.value,
        struct_payment_method=PaymentMethod(id=config.payment_method_id),
    )

    mock_api_access.find_booking_slots.assert_called_once_with(
        expected_find_request_body
    )

    mock_selector.select.assert_called_once_with(slots, request)

    mock_api_access.get_booking_token.assert_called_once_with(
        expected_details_request_body
    )

    mock_api_access.book_slot.assert_called_once_with(expected_booking_request)


def test_check_slots_resolves_venue_name(tmp_path):
    config = ResyConfigFactory.create()
    retries_config = ReservationRetriesConfigFactory.create()
    request = ReservationRequestFactory.create(
        venue_id=None,
        venue_name="Test Venue",
        venue_location="New York",
    )
    mock_api_access = MagicMock()
    mock_api_access.search_venues.return_value = [
        VenueCandidate(
            venue_id="9802",
            name="Test Venue",
            locality="New York",
            region="NY",
        )
    ]
    mock_api_access.get_venue_config.return_value = VenueCandidate(
        venue_id="9802",
        name="Test Venue",
        locality="New York",
        region="NY",
    )
    slots = SlotFactory.create_batch(3)
    mock_api_access.find_booking_slots.return_value = slots
    mock_selector = MagicMock()

    venue_resolver = VenueResolver(
        mock_api_access,
        VenueCache(tmp_path / "venues.db"),
    )
    manager = ResyManager(
        config,
        mock_api_access,
        mock_selector,
        retries_config,
        venue_resolver,
    )

    manager.checkSlots(request)

    expected_day = request.ideal_date.strftime("%Y-%m-%d")
    expected_find_request_body = FindRequestBody(
        venue_id="9802", party_size=request.party_size, day=expected_day
    )

    mock_api_access.search_venues.assert_called_once_with("Test Venue", "New York")
    mock_api_access.find_booking_slots.assert_called_once_with(
        expected_find_request_body
    )


def test_check_slots_with_venue_loads_name_for_venue_id():
    config = ResyConfigFactory.create()
    retries_config = ReservationRetriesConfigFactory.create()
    request = ReservationRequestFactory.create(venue_id="74751")
    mock_api_access = MagicMock()
    mock_api_access.get_venue_config.return_value = VenueCandidate(
        venue_id="74751",
        name="Southeast Impression",
        locality="Fairfax",
        region="VA",
    )
    slots = SlotFactory.create_batch(3)
    mock_api_access.find_booking_slots.return_value = slots
    mock_selector = MagicMock()

    manager = ResyManager(config, mock_api_access, mock_selector, retries_config)

    returned_slots, venue = manager.check_slots_with_venue(request)

    assert returned_slots == slots
    assert venue.name == "Southeast Impression"
    mock_api_access.get_venue_config.assert_called_once_with("74751")


def test_resolve_reservation_request_uses_official_venue_name_for_venue_id():
    config = ResyConfigFactory.create()
    retries_config = ReservationRetriesConfigFactory.create()
    request = ReservationRequestFactory.create(
        venue_id="74751",
        venue_name="typed name",
        venue_location="typed location",
    )
    mock_api_access = MagicMock()
    mock_api_access.get_venue_config.return_value = VenueCandidate(
        venue_id="74751",
        name="Southeast Impression",
        locality="Fairfax",
        region="VA",
    )
    mock_selector = MagicMock()

    manager = ResyManager(config, mock_api_access, mock_selector, retries_config)

    resolved_request = manager.resolve_reservation_request(request)

    assert resolved_request.venue_id == "74751"
    assert resolved_request.venue_name == "Southeast Impression"
    assert resolved_request.venue_location == "Fairfax"
    mock_api_access.get_venue_config.assert_called_once_with("74751")


def test_make_reservation_no_slots():
    config = ResyConfigFactory.create()
    retries_config = ReservationRetriesConfigFactory.create()
    request = ReservationRequestFactory.create()
    mock_api_access = MagicMock()
    mock_api_access.find_booking_slots.return_value = []

    mock_selector = MagicMock()

    manager = ResyManager(config, mock_api_access, mock_selector, retries_config)

    with pytest.raises(NoSlotsError):
        manager.make_reservation(request)


@patch("resy_bot.manager.ResyManager.make_reservation")
def test_make_reservation_with_retries(mock_make_reservation):
    config = ResyConfigFactory.create()
    mock_make_reservation.side_effect = NoSlotsError
    mock_api_access = MagicMock()
    mock_selector = MagicMock()
    retry_config = ReservationRetriesConfig(
        seconds_between_retries=0.1,
        n_retries=10,
    )

    request = ReservationRequestFactory.create()

    manager = ResyManager(config, mock_api_access, mock_selector, retry_config)

    with pytest.raises(ExhaustedRetriesError):
        manager.make_reservation_with_retries(request)

    assert mock_make_reservation.call_count == 10


def test_get_drop_time():
    config = ResyConfigFactory.create()
    mock_api_access = MagicMock()
    mock_selector = MagicMock()
    retry_config = ReservationRetriesConfig(
        seconds_between_retries=0.1,
        n_retries=10,
    )

    request = TimedReservationRequestFactory.create()

    manager = ResyManager(
        config,
        mock_api_access,
        mock_selector,
        retry_config,
        app_timezone=ZoneInfo("America/New_York"),
    )

    drop_time = manager._get_drop_time(
        request,
        datetime(2026, 6, 10, 14, 0, tzinfo=UTC),
    )

    assert drop_time.tzinfo == UTC
    assert drop_time.astimezone(ZoneInfo("America/New_York")).hour == request.expected_drop_hour
    assert drop_time.minute == request.expected_drop_minute


def test_get_drop_time_converts_new_york_time_to_utc():
    config = ResyConfigFactory.create()
    mock_api_access = MagicMock()
    mock_selector = MagicMock()
    retry_config = ReservationRetriesConfig(
        seconds_between_retries=0.1,
        n_retries=10,
    )

    request = TimedReservationRequestFactory.create(
        expected_drop_hour=10,
        expected_drop_minute=30,
    )

    manager = ResyManager(
        config,
        mock_api_access,
        mock_selector,
        retry_config,
        app_timezone=ZoneInfo("America/New_York"),
    )

    drop_time = manager._get_drop_time(
        request,
        datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
    )

    assert drop_time == datetime(2026, 6, 10, 14, 30, tzinfo=UTC)


def test_get_drop_time_uses_next_day_when_drop_time_has_passed():
    config = ResyConfigFactory.create()
    mock_api_access = MagicMock()
    mock_selector = MagicMock()
    retry_config = ReservationRetriesConfig(
        seconds_between_retries=0.1,
        n_retries=10,
    )

    request = TimedReservationRequestFactory.create(
        expected_drop_hour=10,
        expected_drop_minute=30,
    )

    manager = ResyManager(
        config,
        mock_api_access,
        mock_selector,
        retry_config,
        app_timezone=ZoneInfo("America/New_York"),
    )

    drop_time = manager._get_drop_time(
        request,
        datetime(2026, 6, 10, 15, 0, tzinfo=UTC),
    )

    assert drop_time == datetime(2026, 6, 11, 14, 30, tzinfo=UTC)


@patch("resy_bot.manager.ResyManager.make_reservation")
def test_make_reservation_at_opening_time(mock_make_reservation):
    now = datetime(2026, 6, 10, 14, 30, 15, tzinfo=UTC)
    request = TimedReservationRequestFactory.create(
        expected_drop_hour=now.astimezone(ZoneInfo("America/New_York")).hour,
        expected_drop_minute=now.astimezone(ZoneInfo("America/New_York")).minute,
    )

    config = ResyConfigFactory.create()
    mock_api_access = MagicMock()
    mock_selector = MagicMock()
    retry_config = ReservationRetriesConfig(
        seconds_between_retries=0.1,
        n_retries=10,
    )

    manager = ResyManager(
        config,
        mock_api_access,
        mock_selector,
        retry_config,
        app_timezone=ZoneInfo("America/New_York"),
    )

    with patch.object(manager, "_now", return_value=now):
        manager.make_reservation_at_opening_time(request)

    mock_make_reservation.assert_called_once()


@patch("resy_bot.manager.ResyManager.make_reservation")
def test_make_reservation_at_opening_time_checks_slots_in_final_minute(
    mock_make_reservation,
):
    drop_time = datetime(2026, 6, 10, 14, 30, tzinfo=UTC)
    request = TimedReservationRequestFactory.create(
        expected_drop_hour=drop_time.astimezone(ZoneInfo("America/New_York")).hour,
        expected_drop_minute=drop_time.astimezone(ZoneInfo("America/New_York")).minute,
    )

    config = ResyConfigFactory.create()
    mock_api_access = MagicMock()
    mock_selector = MagicMock()
    retry_config = ReservationRetriesConfig(
        seconds_between_retries=0.1,
        n_retries=10,
    )

    manager = ResyManager(
        config,
        mock_api_access,
        mock_selector,
        retry_config,
        app_timezone=ZoneInfo("America/New_York"),
    )
    mock_make_reservation.side_effect = [NoSlotsError, "reservation-token"]
    now_values = [
        drop_time - timedelta(seconds=50),
        drop_time - timedelta(seconds=50),
        drop_time - timedelta(seconds=50),
        drop_time - timedelta(seconds=49, milliseconds=500),
        drop_time - timedelta(seconds=49),
    ]

    with (
        patch.object(manager, "_now", side_effect=now_values),
        patch.object(manager, "_wait") as mock_wait,
    ):
        token = manager.make_reservation_at_opening_time(request)

    assert token == "reservation-token"
    assert mock_make_reservation.call_count == 2
    mock_wait.assert_called_once_with(0.5, None)


@patch("resy_bot.manager.ResyManager.make_reservation")
def test_make_reservation_at_opening_time_honors_retry_limit_after_drop(
    mock_make_reservation,
):
    drop_time = datetime(2026, 6, 10, 14, 30, tzinfo=UTC)
    request = TimedReservationRequestFactory.create(
        expected_drop_hour=drop_time.astimezone(ZoneInfo("America/New_York")).hour,
        expected_drop_minute=drop_time.astimezone(ZoneInfo("America/New_York")).minute,
    )

    config = ResyConfigFactory.create()
    mock_api_access = MagicMock()
    mock_selector = MagicMock()
    retry_config = ReservationRetriesConfig(
        seconds_between_retries=0.1,
        n_retries=2,
    )

    manager = ResyManager(
        config,
        mock_api_access,
        mock_selector,
        retry_config,
        app_timezone=ZoneInfo("America/New_York"),
    )
    mock_make_reservation.side_effect = NoSlotsError
    now_values = [
        drop_time,
        drop_time,
        drop_time,
        drop_time,
        drop_time + timedelta(seconds=1),
    ]

    with (
        pytest.raises(ExhaustedRetriesError),
        patch.object(manager, "_now", side_effect=now_values),
        patch.object(manager, "_wait") as mock_wait,
    ):
        manager.make_reservation_at_opening_time(request)

    assert mock_make_reservation.call_count == 2
    mock_wait.assert_called_once_with(1.0, None)
