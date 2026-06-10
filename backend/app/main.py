import json
from enum import Enum
from os import environ
from threading import Event, Lock
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from requests import HTTPError

from app.env import load_backend_env
from app.job_store import JobStore, StoredJob
import app.services.reservation_service as reservation_service
from resy_bot.errors import ExhaustedRetriesError, NoSlotsError, ReservationCancelledError
from resy_bot.models import (
    ReservationRequest,
    ResolvedVenue,
    Slot,
    TimedReservationRequest,
)


load_backend_env()

app = FastAPI(title="Resy Bot")
job_store = JobStore()


def _cors_origins() -> list[str]:
    origins = environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ReserveResponse(BaseModel):
    job_id: str
    status: JobStatus


class ReservationDetails(BaseModel):
    restaurant_name: str | None = None
    venue_id: str | None = None
    venue_location: str | None = None
    party_size: int | None = None
    ideal_date: str | None = None
    days_in_advance: int | None = None
    ideal_time: str | None = None
    window_hours: int | None = None
    prefer_early: bool | None = None
    preferred_type: str | None = None
    method: str | None = None
    expected_drop_time: str | None = None


class ReservationJob(BaseModel):
    id: str
    status: JobStatus
    created_at: str
    updated_at: str
    reservation: ReservationDetails | None = None
    reservation_token: str | None = None
    error: str | None = None


class SlotsResponse(BaseModel):
    venue: ResolvedVenue | None = None
    slots: list[Slot] = Field(default_factory=list)


cancellation_events: dict[str, Event] = {}
jobs_lock = Lock()


@app.on_event("startup")
def mark_interrupted_jobs() -> None:
    job_store.mark_active_interrupted()


def _to_response_job(job: StoredJob) -> ReservationJob:
    return ReservationJob(
        id=job.id,
        status=JobStatus(job.status),
        created_at=job.created_at,
        updated_at=job.updated_at,
        reservation=_job_reservation_details(job),
        reservation_token=job.reservation_token,
        error=job.error,
    )


def _format_time(hour: object, minute: object) -> str | None:
    if not isinstance(hour, int) or not isinstance(minute, int):
        return None

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None

    period = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12 or 12
    return f"{hour_12}:{minute:02d} {period}"


def _job_reservation_details(job: StoredJob) -> ReservationDetails | None:
    try:
        request = json.loads(job.request_json)
    except json.JSONDecodeError:
        return None

    reservation_request = request.get("reservation_request")
    if not isinstance(reservation_request, dict):
        return None

    return ReservationDetails(
        restaurant_name=reservation_request.get("venue_name"),
        venue_id=reservation_request.get("venue_id"),
        venue_location=reservation_request.get("venue_location"),
        party_size=reservation_request.get("party_size"),
        ideal_date=reservation_request.get("ideal_date"),
        days_in_advance=reservation_request.get("days_in_advance"),
        ideal_time=_format_time(
            reservation_request.get("ideal_hour"),
            reservation_request.get("ideal_minute"),
        ),
        window_hours=reservation_request.get("window_hours"),
        prefer_early=reservation_request.get("prefer_early"),
        preferred_type=reservation_request.get("preferred_type"),
        method=reservation_request.get("method"),
        expected_drop_time=_format_time(
            request.get("expected_drop_hour"),
            request.get("expected_drop_minute"),
        ),
    )


def _set_job(
    job_id: str,
    status: JobStatus,
    *,
    reservation_token: str | None = None,
    error: str | None = None,
) -> None:
    job_store.set_job(
        job_id,
        status.value,
        reservation_token=reservation_token,
        error=error,
    )


def _map_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, NoSlotsError):
        return HTTPException(status_code=404, detail=str(exc))

    if isinstance(exc, ExhaustedRetriesError):
        return HTTPException(status_code=408, detail=str(exc))

    if isinstance(exc, ReservationCancelledError):
        return HTTPException(status_code=409, detail=str(exc))

    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))

    if isinstance(exc, HTTPError):
        return HTTPException(status_code=502, detail=str(exc))

    return HTTPException(status_code=500, detail="Unexpected reservation error")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    messages = [
        str(error.get("msg", "Invalid request")).replace("Value error, ", "")
        for error in errors
    ]

    return JSONResponse(
        status_code=400,
        content={"detail": " ".join(messages) or "Invalid request"},
    )


def _run_reservation_job(job_id: str, request: TimedReservationRequest) -> None:
    with jobs_lock:
        cancel_event = cancellation_events[job_id]

    if cancel_event.is_set():
        _set_job(
            job_id,
            JobStatus.CANCELLED,
            error="Reservation job was cancelled",
        )
        return

    _set_job(job_id, JobStatus.RUNNING)

    try:
        reservation_token = reservation_service.reserve(
            request.model_dump(),
            cancel_event=cancel_event,
        )
    except ReservationCancelledError as exc:
        _set_job(job_id, JobStatus.CANCELLED, error=str(exc))
        return
    except Exception as exc:
        _set_job(job_id, JobStatus.FAILED, error=_map_exception(exc).detail)
        return

    _set_job(
        job_id,
        JobStatus.SUCCEEDED,
        reservation_token=reservation_token,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/slots", response_model=SlotsResponse)
async def slots(request: ReservationRequest) -> SlotsResponse:
    try:
        found_slots, venue = await run_in_threadpool(
            reservation_service.check_slots_with_venue,
            request.model_dump(),
        )
    except Exception as exc:
        raise _map_exception(exc) from exc

    return SlotsResponse(venue=venue, slots=found_slots)


@app.post("/reserve", response_model=ReserveResponse, status_code=202)
async def reserve(
    request: TimedReservationRequest, background_tasks: BackgroundTasks
) -> ReserveResponse:
    job_id = str(uuid4())
    job_store.create_job(
        job_id,
        JobStatus.PENDING.value,
        request.model_dump(mode="json"),
    )

    with jobs_lock:
        cancellation_events[job_id] = Event()

    background_tasks.add_task(_run_reservation_job, job_id, request)

    return ReserveResponse(job_id=job_id, status=JobStatus.PENDING)


@app.get("/jobs", response_model=list[ReservationJob])
def list_jobs() -> list[ReservationJob]:
    return [_to_response_job(job) for job in job_store.list_jobs()]


@app.get("/jobs/{job_id}", response_model=ReservationJob)
def get_job(job_id: str) -> ReservationJob:
    job = job_store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return _to_response_job(job)


@app.post("/jobs/{job_id}/cancel", response_model=ReservationJob)
def cancel_job(job_id: str) -> ReservationJob:
    job = job_store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response_job = _to_response_job(job)

    if response_job.status in {
        JobStatus.SUCCEEDED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    }:
        return response_job

    with jobs_lock:
        cancel_event = cancellation_events.get(job_id)

        if cancel_event:
            cancel_event.set()

    cancelled_job = job_store.request_cancel(
        job_id,
        JobStatus.CANCELLING.value,
        "Cancellation requested",
    )

    if not cancelled_job:
        raise HTTPException(status_code=404, detail="Job not found")

    return _to_response_job(cancelled_job)
