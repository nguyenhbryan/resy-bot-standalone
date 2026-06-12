from datetime import date
from resy_bot.models import (
    ReservationRequest,
    AuthRequestBody,
    FindRequestBody,
    DetailsRequestBody,
    Slot,
    DetailsResponseBody,
    BookRequestBody,
    ResyConfig,
    PaymentMethod,
)


def build_find_request_body(
    reservation: ReservationRequest, target_date: date | None = None
) -> FindRequestBody:
    day = date.strftime(target_date or reservation.target_date, "%Y-%m-%d")

    return FindRequestBody(
        venue_id=reservation.resolved_venue_id,
        party_size=reservation.party_size,
        long="0",
        lat="0",
        day=day,
    )


def build_get_slot_details_body(
    reservation: ReservationRequest, slot: Slot, target_date: date | None = None
) -> DetailsRequestBody:
    day = date.strftime(target_date or reservation.target_date, "%Y-%m-%d")
    config_id = slot.config.token

    return DetailsRequestBody(
        config_id=config_id,
        day=day,
        party_size=reservation.party_size,
    )


def build_auth_request_body(config: ResyConfig) -> AuthRequestBody:
    return AuthRequestBody(email=config.email, password=config.password)


def build_book_request_body(
    details: DetailsResponseBody, config: ResyConfig
) -> BookRequestBody:
    payment_method = PaymentMethod(id=config.payment_method_id)
    return BookRequestBody(
        book_token=details.book_token.value, struct_payment_method=payment_method
    )
