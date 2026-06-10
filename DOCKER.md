# Docker

Run the full app on Linux with Docker Compose:

```bash
docker compose up --build
```

The frontend is available at http://localhost:3000 and the FastAPI backend is available at http://localhost:8000.

## Configuration

Runtime secrets stay outside the images:

- `backend/.env` provides Resy credentials and backend settings. Start from `backend/.env.example` if needed.
- `frontend/.env` should provide `ACCESS_KEY`.

Compose sets `FASTAPI_URL=http://backend:8000` for the frontend container so server actions call the backend over the Compose network.

Useful commands:

```bash
docker compose up --build
docker compose down
docker compose logs -f backend
docker compose logs -f frontend
```
