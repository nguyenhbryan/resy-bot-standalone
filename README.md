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

- Check available Resy slots for a venue, date or days-in-advance window, party size, and seating type.
- Schedule reservation attempts around an expected drop time.
- Track reservation jobs with `pending`, `running`, `cancelling`, `cancelled`, `succeeded`, and `failed` statuses.
- Cancel active reservation jobs.
- Persist backend job state in SQLite.
- Run locally with Docker Compose or run the backend and frontend separately.

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
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

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
- `POST /slots` - check availability for a reservation request.
- `POST /reserve` - create a background reservation job.
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
