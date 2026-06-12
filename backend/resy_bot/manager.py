import time
from datetime import UTC, datetime, timedelta
from os import environ
from threading import Event
from typing import List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from resy_bot.logging_config import logging
from resy_bot.errors import (
    ExhaustedRetriesError,
    NoSlotsError,
    ReservationCancelledError,
)
from resy_bot.constants import (
    N_RETRIES,
    SECONDS_TO_WAIT_BETWEEN_RETRIES,
)
from resy_bot.models import (
    ResyConfig,
    ReservationRequest,
    ResolvedVenue,
    TimedReservationRequest,
    ReservationRetriesConfig,
)
from resy_bot.model_builders import (
    build_find_request_body,
    build_get_slot_details_body,
    build_book_request_body,
)
from resy_bot.api_access import ResyApiAccess, Slot
from resy_bot.selectors import AbstractSelector, SimpleSelector
from resy_bot.venue_resolver import VenueCandidate, VenueResolver

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

DEFAULT_APP_TIMEZONE = "America/New_York"
FINAL_DROP_POLLING_WINDOW = timedelta(minutes=1)
MIN_SECONDS_BETWEEN_SLOT_CHECKS = 1.0


def _load_app_timezone() -> ZoneInfo:
    timezone_name = environ.get("APP_TIMEZONE", DEFAULT_APP_TIMEZONE)

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Invalid APP_TIMEZONE {timezone_name!r}; use an IANA timezone "
            "like 'America/New_York'."
        ) from exc


def _raise_if_cancelled(cancel_event: Event | None) -> None:
    if cancel_event and cancel_event.is_set():
        raise ReservationCancelledError("Reservation job was cancelled")


class ResyManager:
    @classmethod
    def build(cls, config: ResyConfig) -> "ResyManager":
        api_access = ResyApiAccess.build(config)
        selector = SimpleSelector()
        retry_config = ReservationRetriesConfig(
            seconds_between_retries=SECONDS_TO_WAIT_BETWEEN_RETRIES,
            n_retries=N_RETRIES,
        )
        return cls(config, api_access, selector, retry_config)

    def __init__(
        self,
        config: ResyConfig,
        api_access: ResyApiAccess,
        slot_selector: AbstractSelector,
        retry_config: ReservationRetriesConfig,
        venue_resolver: VenueResolver | None = None,
        app_timezone: ZoneInfo | None = None,
    ):
        self.config = config
        self.api_access = api_access
        self.selector = slot_selector
        self.retry_config = retry_config
        self.venue_resolver = venue_resolver or VenueResolver(api_access)
        self.app_timezone = app_timezone or _load_app_timezone()

    def get_venue_id(self, name: str, location: str | None = None) -> str:
        return self.venue_resolver.resolve(name, location)

    def get_venue(self, name: str, location: str | None = None) -> ResolvedVenue:
        return self._to_resolved_venue(
            self.venue_resolver.resolve_candidate(name, location)
        )

    def resolve_reservation_request(
        self,
        reservation_request: ReservationRequest,
    ) -> ReservationRequest:
        resolved_request, venue = self._resolve_request_venue(
            reservation_request,
            include_venue_info=True,
        )

        if not venue:
            return resolved_request

        return resolved_request.model_copy(
            update={
                "venue_id": venue.venue_id,
                "venue_name": venue.name,
                "venue_location": venue.locality or resolved_request.venue_location,
            }
        )

    def _resolve_request_venue(
        self,
        reservation_request: ReservationRequest,
        include_venue_info: bool = False,
    ) -> tuple[ReservationRequest, ResolvedVenue | None]:
        if reservation_request.venue_id:
            venue = (
                self._get_venue_config(reservation_request.venue_id)
                if include_venue_info
                else None
            )
            if not venue and reservation_request.venue_name:
                venue = ResolvedVenue(
                    venue_id=reservation_request.venue_id,
                    name=reservation_request.venue_name,
                    locality=reservation_request.venue_location,
                )
            return reservation_request, venue

        if not reservation_request.venue_name:
            raise ValueError("Must provide venue_id or venue_name")

        candidate = self.venue_resolver.resolve_candidate(
            reservation_request.venue_name,
            reservation_request.venue_location,
        )
        venue = self._to_resolved_venue(candidate)

        return (
            reservation_request.model_copy(
                update={"venue_id": venue.venue_id, "venue_name": venue.name}
            ),
            venue,
        )

    def _to_resolved_venue(self, candidate: VenueCandidate) -> ResolvedVenue:
        return ResolvedVenue(
            venue_id=candidate.venue_id,
            name=candidate.name,
            locality=candidate.locality,
            region=candidate.region,
        )

    def _get_venue_config(self, venue_id: str) -> ResolvedVenue | None:
        candidate = self.api_access.get_venue_config(venue_id)

        if not candidate:
            return None

        return self._to_resolved_venue(candidate)

    def checkSlots(self, reservation_request: ReservationRequest) -> List[Slot]:
        reservation_request, _ = self._resolve_request_venue(reservation_request)
        body = build_find_request_body(reservation_request)
        slots = self.api_access.find_booking_slots(body)
        return slots;

    def check_slots_with_venue(
        self, reservation_request: ReservationRequest
    ) -> tuple[List[Slot], ResolvedVenue | None]:
        reservation_request, venue = self._resolve_request_venue(
            reservation_request,
            include_venue_info=True,
        )
        body = build_find_request_body(reservation_request)
        slots = self.api_access.find_booking_slots(body)
        return slots, venue


    def make_reservation(self, reservation_request: ReservationRequest) -> str:
        reservation_request, _ = self._resolve_request_venue(reservation_request)
        body = build_find_request_body(reservation_request)

        slots = self.api_access.find_booking_slots(body)
        logger.info(f"Returned: {slots}")

        if len(slots) == 0:
            raise NoSlotsError("No Slots Found")
        else:
            logger.info(len(slots))
            logger.info(slots)

        selected_slot = self.selector.select(slots, reservation_request)

        logger.info(selected_slot)
        details_request = build_get_slot_details_body(
            reservation_request, selected_slot
        )
        logger.info(details_request)
        token = self.api_access.get_booking_token(details_request)

        booking_request = build_book_request_body(token, self.config)

        resy_token = self.api_access.book_slot(booking_request)

        return resy_token

    def make_reservation_with_retries(
        self,
        reservation_request: ReservationRequest,
        cancel_event: Event | None = None,
    ) -> str:
        for _ in range(self.retry_config.n_retries):
            _raise_if_cancelled(cancel_event)

            try:
                return self.make_reservation(reservation_request)

            except NoSlotsError:
                logger.info(
                    f"no slots, retrying; currently {datetime.now().isoformat()}"
                )
                if cancel_event:
                    cancel_event.wait(self.retry_config.seconds_between_retries)
                else:
                    time.sleep(self.retry_config.seconds_between_retries)

        raise ExhaustedRetriesError(
            f"Retried {self.retry_config.n_retries} times, " "without finding a slot"
        )

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _seconds_between_slot_checks(self) -> float:
        return max(
            MIN_SECONDS_BETWEEN_SLOT_CHECKS,
            self.retry_config.seconds_between_retries,
        )

    def _wait(self, seconds: float, cancel_event: Event | None = None) -> None:
        if seconds <= 0:
            return

        if cancel_event:
            cancel_event.wait(seconds)
        else:
            time.sleep(seconds)

    def _get_drop_time(
        self,
        reservation_request: TimedReservationRequest,
        now: datetime | None = None,
    ) -> datetime:
        local_now = (now or self._now()).astimezone(self.app_timezone)
        local_drop_time = datetime(
            year=local_now.year,
            month=local_now.month,
            day=local_now.day,
            hour=reservation_request.expected_drop_hour,
            minute=reservation_request.expected_drop_minute,
            tzinfo=self.app_timezone,
        )
        local_now_minute = local_now.replace(second=0, microsecond=0)
        if local_drop_time < local_now_minute:
            local_drop_time += timedelta(days=1)

        return local_drop_time.astimezone(UTC)

    def make_reservation_at_opening_time(
        self,
        reservation_request: TimedReservationRequest,
        cancel_event: Event | None = None,
    ) -> str:
        """
        cycle until we hit the opening time, then run & return the reservation
        """
        drop_time = self._get_drop_time(reservation_request)
        polling_starts_at = drop_time - FINAL_DROP_POLLING_WINDOW
        status_logged_at = self._now()
        last_slot_check: datetime | None = None
        post_drop_attempts = 0

        while True:
            _raise_if_cancelled(cancel_event)

            now = self._now()
            if now < polling_starts_at:
                if now - status_logged_at > timedelta(seconds=10):
                    logger.info(f"{now}: still waiting")
                    status_logged_at = now
                self._wait(0.25, cancel_event)
                continue

            seconds_between_checks = self._seconds_between_slot_checks()
            if last_slot_check:
                seconds_since_last_check = (now - last_slot_check).total_seconds()
                if seconds_since_last_check < seconds_between_checks:
                    self._wait(
                        seconds_between_checks - seconds_since_last_check,
                        cancel_event,
                    )
                    continue

            logger.info(f"checking for slots now! {now}")
            last_slot_check = now

            try:
                return self.make_reservation(reservation_request.reservation_request)
            except NoSlotsError:
                if now >= drop_time:
                    post_drop_attempts += 1
                    if post_drop_attempts >= self.retry_config.n_retries:
                        raise ExhaustedRetriesError(
                            f"Retried {self.retry_config.n_retries} times, "
                            "without finding a slot"
                        )

                logger.info(f"no slots, retrying; currently {now.isoformat()}")
