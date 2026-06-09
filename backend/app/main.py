from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

import backend.app.services.reservation_service as reservation_service
from backend.resy_bot.models import ResyConfig, TimedReservationRequest


app = FastAPI(title="Resy Bot")


class ReserveRequest(BaseModel):
    resy_config: ResyConfig
    reservation_request: TimedReservationRequest


class ReserveResponse(BaseModel):
    reservation_token: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reserve", response_model=ReserveResponse)
async def reserve(request: ReserveRequest) -> ReserveResponse:
    try:
        reservation_token = await run_in_threadpool(
            reservation_service.reserve,
            request.resy_config.model_dump(),
            request.reservation_request.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ReserveResponse(reservation_token=reservation_token)
