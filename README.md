# Resy Bot

Resy Bot is a full-stack reservation console for checking Resy availability and scheduling reservation attempts when tables are expected to drop. It combines a FastAPI backend that talks to Resy with a Next.js frontend for entering search criteria, checking slots, starting jobs, and cancelling active jobs.

Use it responsibly with your own Resy account credentials and payment method. The app performs real reservation actions against Resy APIs.

## Project Structure

```text
.
├── backend/      FastAPI app, Resy client logic, tests, and reservation JSON examples
├── frontend/     Next.js app with an access-key gate and reservation console
├── compose.yaml  Docker Compose stack for backend + frontend
└── DOCKER.md     Docker-specific notes
```

## Features

- Check available Resy slots by venue ID or by venue name plus optional city/region.
- Resolve and cache venue search results so users do not need to manually inspect Resy network traffic for every venue ID.
- Check slots for a specific date or days-in-advance window, party size, ideal time, time window, and seating type.
- Schedule reservation attempts around an expected drop time.
- Enter user-facing times in 12-hour format, such as `7:30 PM` or `10 AM`; the frontend converts them for the backend.
- Track reservation jobs with `pending`, `running`, `cancelling`, `cancelled`, `succeeded`, and `failed` statuses.
- List recent reservation jobs with timestamps and errors.
- Cancel active reservation jobs.
- Persist backend job state in SQLite.
- Gate the web console behind an `ACCESS_KEY` cookie.
- Run locally with Docker Compose or run the backend and frontend separately.

## Pull Request Highlights

This update turns the app into a more complete reservation console instead of a thin form over the backend.

- Lazy loading and dynamic server rendering: the protected Next.js console is rendered as a dynamic route and loads live backend data only after the access key has been accepted. API health, selected job state, and the job list are fetched on demand for each console view, while available slots are loaded only after the user submits `Check Slots`.
- Venue search: reservation requests can now use `venue_name` and optional `venue_location`; the backend searches Resy, ranks matches, caches resolved venues in SQLite, and still supports direct `venue_id` entry.
- Job management: reservation jobs are persisted with created/updated timestamps, exposed through a list endpoint, and shown in the frontend with status, errors, reservation tokens, and cancellation controls.
- Time picker fix: the frontend accepts natural 12-hour times with AM/PM for both ideal reservation time and expected drop time, then converts those values to backend hour/minute fields.
- Resilience and feedback: the console shows API health, disables reservation actions while FastAPI is offline, and surfaces backend validation or Resy errors in the UI.
- Test coverage: backend tests cover venue search/resolution, API parsing, slot checks with venue metadata, job listing/persistence, and time-sensitive reservation behavior.

## Requirements

- Docker and Docker Compose for the easiest full-stack setup.
- Python 3.11+ for local backend development.
- `uv` or Poetry-compatible tooling for backend dependency management.
- Bun 1.3+ for frontend development.

## Configuration

Create `backend/.env` from the provided example:

```bash
cp backend/.env.example backend/.env
```

Set these backend values:

```env
RESY_API_KEY=your_resy_api_key
RESY_TOKEN=your_resy_auth_token
RESY_PAYMENT_METHOD_ID=123456
RESY_EMAIL=you@example.com
RESY_PASSWORD=your_resy_password
APP_TIMEZONE=America/New_York
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SQLITE_PATH=/tmp/resy-bot-jobs.db
RESY_VENUE_CACHE_PATH=/tmp/resy-bot-venues.db
```

Scheduled drop times are interpreted in `APP_TIMEZONE` and converted to UTC
internally, so Docker containers can keep their default UTC clock. Use an IANA
timezone like `America/New_York` instead of `EDT` so daylight saving time is
handled automatically.

Create `frontend/.env` with an access key for the web console:

```env
ACCESS_KEY=choose-a-local-console-password
FASTAPI_URL=http://127.0.0.1:8000
```

When running with Docker Compose, `FASTAPI_URL` is set to `http://backend:8000` in `compose.yaml`, so the frontend container can reach the backend over the Compose network.

## Run With Docker

From the repository root:

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health

Useful commands:

```bash
docker compose down
docker compose logs -f backend
docker compose logs -f frontend
```

## Run Locally

Start the backend:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Start the frontend in a second terminal:

```bash
cd frontend
bun install
bun run dev
```

Open http://localhost:3000 and enter the `ACCESS_KEY` from `frontend/.env`.

## Backend API

The FastAPI app exposes:

- `GET /health` - backend health check.
- `POST /slots` - check availability for a reservation request and return matching venue metadata when available.
- `POST /reserve` - create a background reservation job.
- `GET /jobs` - list reservation jobs, newest first.
- `GET /jobs/{job_id}` - fetch reservation job status.
- `POST /jobs/{job_id}/cancel` - request cancellation for an active job.

See [backend/README.md](backend/README.md) for detailed Resy credential and reservation request field notes.

## Tests

Run backend tests from `backend/`:

```bash
uv run pytest
```

Run frontend linting from `frontend/`:

```bash
bun run lint
```

## Notes

- Resy credentials are loaded from `backend/.env`; do not commit real credentials.
- The frontend requires `ACCESS_KEY` before it will show the reservation console.
- Docker Compose stores backend jobs in a named `backend_data` volume.
- Existing example request payloads live in `backend/reservation_jsons/`.
