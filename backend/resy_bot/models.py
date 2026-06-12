from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from enum import Enum

from pydantic import BaseModel, validator, model_validator, field_validator

class BookingMethod(str, Enum):
    MONITOR = "monitor";
    SCHEDULED = "scheduled";

class ResyConfig(BaseModel):
    api_key: str
    token: str
    payment_method_id: int
    email: str
    password: str

    def get_authorization(self) -> str:
        return f'ResyAPI api_key="{self.api_key}"'


class ReservationRequest(BaseModel):
    venue_id: Optional[str] = None
    venue_name: Optional[str] = None
    venue_location: Optional[str] = None
    party_size: int
    ideal_hour: int
    ideal_minute: int
    window_hours: int
    prefer_early: bool
    preferred_type: Optional[str]
    ideal_date: Optional[date] = None
    days_in_advance: Optional[int] = None
    monitor_dates: Optional[List[date]] = None
    method: BookingMethod

    @model_validator(mode="before")
    def validate_request(cls, values: Dict) -> Dict:
        # Coerce common date string formats to `date`
        ideal = values.get("ideal_date")
        if isinstance(ideal, str):
            for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%m/%d/%Y"):
                try:
                    values["ideal_date"] = datetime.strptime(ideal, fmt).date()
                    break
                except Exception:
                    continue

        monitor_dates = values.get("monitor_dates")
        if monitor_dates is not None:
            if not isinstance(monitor_dates, list):
                monitor_dates = [monitor_dates]

            parsed_monitor_dates = []
            seen_monitor_dates = set()
            for monitor_date in monitor_dates:
                parsed_date = monitor_date
                if isinstance(monitor_date, str):
                    parsed_date = None
                    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%m/%d/%Y"):
                        try:
                            parsed_date = datetime.strptime(monitor_date, fmt).date()
                            break
                        except Exception:
                            continue

                if isinstance(parsed_date, datetime):
                    parsed_date = parsed_date.date()

                if isinstance(parsed_date, date) and parsed_date not in seen_monitor_dates:
                    parsed_monitor_dates.append(parsed_date)
                    seen_monitor_dates.add(parsed_date)

            values["monitor_dates"] = parsed_monitor_dates or None

        method = values.get("method")
        if method == BookingMethod.MONITOR or method == BookingMethod.MONITOR.value:
            if values.get("days_in_advance") is not None:
                raise ValueError("Monitor requests must use monitor_dates, not days_in_advance")

            if not values.get("monitor_dates") and values.get("ideal_date") is not None:
                values["monitor_dates"] = [values["ideal_date"]]

            if not values.get("monitor_dates"):
                raise ValueError("Monitor requests must provide at least one monitor date")

            return cls._validate_venue(values)

        has_date = values.get("ideal_date") is not None
        has_waiting_pd = values.get("days_in_advance") is not None

        if values.get("monitor_dates"):
            raise ValueError("Scheduled requests must use ideal_date or days_in_advance, not monitor_dates")

        if has_date and has_waiting_pd:
            raise ValueError("Must only provide one of ideal_date or days_in_advance")
        elif has_date or has_waiting_pd:
            pass
        else:
            raise ValueError("Must provide ideal_date or days_in_advance")

        return cls._validate_venue(values)

    @classmethod
    def _validate_venue(cls, values: Dict) -> Dict:
        venue_id = values.get("venue_id")
        venue_name = values.get("venue_name")

        if isinstance(venue_id, str):
            venue_id = venue_id.strip()
            values["venue_id"] = venue_id or None

        if isinstance(venue_name, str):
            venue_name = venue_name.strip()
            values["venue_name"] = venue_name or None

        if not values.get("venue_id") and not values.get("venue_name"):
            raise ValueError("Must provide venue_id or venue_name")

        return values

    @property
    def resolved_venue_id(self) -> str:
        if not self.venue_id:
            raise ValueError("Venue name has not been resolved to a venue_id")

        return self.venue_id

    @property
    def target_date(self) -> date:
        if self.ideal_date:
            return self.ideal_date

        if self.days_in_advance:
            return date.today() + timedelta(days=self.days_in_advance)

        if self.monitor_dates:
            return self.monitor_dates[0]

        raise ValueError("No date")

    @property
    def target_dates(self) -> List[date]:
        if self.method == BookingMethod.MONITOR:
            if not self.monitor_dates:
                raise ValueError("No monitor dates")
            return self.monitor_dates

        return [self.target_date]


class ReservationRetriesConfig(BaseModel):
    seconds_between_retries: float
    n_retries: int


class TimedReservationRequest(BaseModel):
    reservation_request: ReservationRequest
    expected_drop_hour: int
    expected_drop_minute: int


class ResolvedVenue(BaseModel):
    venue_id: str
    name: str
    locality: Optional[str] = None
    region: Optional[str] = None


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
