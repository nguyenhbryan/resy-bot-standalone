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
import app.services.reservation_service as reservation_service
from resy_bot.errors import ExhaustedRetriesError, NoSlotsError, ReservationCancelledError
from resy_bot.models import ReservationRequest, Slot, TimedReservationRequest


load_backend_env()

app = FastAPI(title="Resy Bot")


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


class ReservationJob(BaseModel):
    id: str
    status: JobStatus
    reservation_token: str | None = None
    error: str | None = None


class SlotsResponse(BaseModel):
    slots: list[Slot] = Field(default_factory=list)


jobs: dict[str, ReservationJob] = {}
cancellation_events: dict[str, Event] = {}
jobs_lock = Lock()


def _set_job(job: ReservationJob) -> None:
    with jobs_lock:
        jobs[job.id] = job


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
            ReservationJob(
                id=job_id,
                status=JobStatus.CANCELLED,
                error="Reservation job was cancelled",
            )
        )
        return

    _set_job(ReservationJob(id=job_id, status=JobStatus.RUNNING))

    try:
        reservation_token = reservation_service.reserve(
            request.model_dump(),
            cancel_event=cancel_event,
        )
    except ReservationCancelledError as exc:
        _set_job(
            ReservationJob(
                id=job_id,
                status=JobStatus.CANCELLED,
                error=str(exc),
            )
        )
        return
    except Exception as exc:
        _set_job(
            ReservationJob(
                id=job_id,
                status=JobStatus.FAILED,
                error=_map_exception(exc).detail,
            )
        )
        return

    _set_job(
        ReservationJob(
            id=job_id,
            status=JobStatus.SUCCEEDED,
            reservation_token=reservation_token,
        )
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/slots", response_model=SlotsResponse)
async def slots(request: ReservationRequest) -> SlotsResponse:
    try:
        found_slots = await run_in_threadpool(
            reservation_service.check_slots,
            request.model_dump(),
        )
    except Exception as exc:
        raise _map_exception(exc) from exc

    return SlotsResponse(slots=found_slots)


@app.post("/reserve", response_model=ReserveResponse, status_code=202)
async def reserve(
    request: TimedReservationRequest, background_tasks: BackgroundTasks
) -> ReserveResponse:
    job_id = str(uuid4())
    with jobs_lock:
        jobs[job_id] = ReservationJob(id=job_id, status=JobStatus.PENDING)
        cancellation_events[job_id] = Event()

    background_tasks.add_task(_run_reservation_job, job_id, request)

    return ReserveResponse(job_id=job_id, status=JobStatus.PENDING)


@app.get("/jobs/{job_id}", response_model=ReservationJob)
def get_job(job_id: str) -> ReservationJob:
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@app.post("/jobs/{job_id}/cancel", response_model=ReservationJob)
def cancel_job(job_id: str) -> ReservationJob:
    with jobs_lock:
        job = jobs.get(job_id)
        cancel_event = cancellation_events.get(job_id)

        if not job or not cancel_event:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }:
            return job

        cancel_event.set()
        job = ReservationJob(
            id=job.id,
            status=JobStatus.CANCELLING,
            reservation_token=job.reservation_token,
            error="Cancellation requested",
        )
        jobs[job_id] = job

    return job
