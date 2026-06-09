from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta

from pydantic import BaseModel, validator, model_validator, field_validator


class ResyConfig(BaseModel):
    api_key: str
    token: str
    payment_method_id: int
    email: str
    password: str

    def get_authorization(self) -> str:
        return f'ResyAPI api_key="{self.api_key}"'


class ReservationRequest(BaseModel):
    venue_id: str
    party_size: int
    ideal_hour: int
    ideal_minute: int
    window_hours: int
    prefer_early: bool
    preferred_type: Optional[str]
    ideal_date: Optional[date] = None
    days_in_advance: Optional[int] = None

    @model_validator(mode="before")
    def validate_target_date(cls, values: Dict) -> Dict:
        # Coerce common date string formats to `date`
        ideal = values.get("ideal_date")
        if isinstance(ideal, str):
            for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%m/%d/%Y"):
                try:
                    values["ideal_date"] = datetime.strptime(ideal, fmt).date()
                    break
                except Exception:
                    continue

        has_date = values.get("ideal_date") is not None
        has_waiting_pd = values.get("days_in_advance") is not None

        if has_date and has_waiting_pd:
            raise ValueError("Must only provide one of ideal_date or days_in_advance")
        elif has_date or has_waiting_pd:
            return values

        raise ValueError("Must provide ideal_date or days_in_advance")

    @property
    def target_date(self) -> date:
        if self.ideal_date:
            return self.ideal_date

        if self.days_in_advance:
            return date.today() + timedelta(days=self.days_in_advance)

        raise ValueError("No date")


class ReservationRetriesConfig(BaseModel):
    seconds_between_retries: float
    n_retries: int


class TimedReservationRequest(BaseModel):
    reservation_request: ReservationRequest
    expected_drop_hour: int
    expected_drop_minute: int


class AuthRequestBody(BaseModel):
    email: str
    password: str


class PaymentMethod(BaseModel):
    id: int


class AuthResponseBody(BaseModel):
    payment_methods: List[PaymentMethod]
    token: str


class FindRequestBody(BaseModel):
    lat: str = "0"
    long: str = "0"
    day: str
    party_size: int
    venue_id: Optional[str]

    @validator("day")
    def validate_day(cls, day: str) -> str:
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Day must be in isoformat")

        return day


class SlotConfig(BaseModel):
    id: str
    type: str
    token: str

    @field_validator("id", mode="before")
    def coerce_id(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)

    @field_validator("type", mode="before")
    def coerce_type(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)

    @field_validator("token", mode="before")
    def coerce_token(cls, v: Any) -> str:
        if v is None:
            return v
        return str(v)


class SlotDate(BaseModel):
    start: datetime
    end: datetime


class Slot(BaseModel):
    config: SlotConfig
    date: SlotDate


class Venue(BaseModel):
    slots: List[Slot]


class Results(BaseModel):
    venues: List[Venue]


class FindResponseBody(BaseModel):
    results: Results


class DetailsRequestBody(BaseModel):
    config_id: str
    party_size: int
    day: str


class BookToken(BaseModel):
    date_expires: datetime
    value: str


class DetailsResponseBody(BaseModel):
    book_token: BookToken


class BookRequestBody(BaseModel):
    book_token: str
    struct_payment_method: PaymentMethod
    source_id: str = "resy.com-venue-details"


class BookResponseBody(BaseModel):
    resy_token: str
