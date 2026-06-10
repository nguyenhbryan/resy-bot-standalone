import time
from datetime import datetime, timedelta
from threading import Event
from typing import List

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
    ):
        self.config = config
        self.api_access = api_access
        self.selector = slot_selector
        self.retry_config = retry_config
        self.venue_resolver = venue_resolver or VenueResolver(api_access)

    def get_venue_id(self, name: str, location: str | None = None) -> str:
        return self.venue_resolver.resolve(name, location)

    def get_venue(self, name: str, location: str | None = None) -> ResolvedVenue:
        return self._to_resolved_venue(
            self.venue_resolver.resolve_candidate(name, location)
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

    def _get_drop_time(self, reservation_request: TimedReservationRequest) -> datetime:
        now = datetime.now()
        return datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=reservation_request.expected_drop_hour,
            minute=reservation_request.expected_drop_minute,
        )

    def make_reservation_at_opening_time(
        self,
        reservation_request: TimedReservationRequest,
        cancel_event: Event | None = None,
    ) -> str:
        """
        cycle until we hit the opening time, then run & return the reservation
        """
        drop_time = self._get_drop_time(reservation_request)
        last_check = datetime.now()

        while True:
            _raise_if_cancelled(cancel_event)

            if datetime.now() < drop_time:
                if datetime.now() - last_check > timedelta(seconds=10):
                    logger.info(f"{datetime.now()}: still waiting")
                    last_check = datetime.now()
                if cancel_event:
                    cancel_event.wait(0.25)
                else:
                    time.sleep(0.25)
                continue

            logger.info(f"time reached, making a reservation now! {datetime.now()}")
            return self.make_reservation_with_retries(
                reservation_request.reservation_request,
                cancel_event,
            )
