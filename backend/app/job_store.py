import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from os import environ
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse, unquote


@dataclass(frozen=True)
class StoredJob:
    id: str
    status: str
    request_json: str
    created_at: str
    updated_at: str
    reservation_token: str | None = None
    error: str | None = None
    cancel_requested: bool = False


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _database_path() -> Path:
    database_url = environ.get("DATABASE_URL")

    if database_url:
        parsed = urlparse(database_url)

        if parsed.scheme != "sqlite":
            raise ValueError("Only sqlite DATABASE_URL values are supported")

        if parsed.netloc and parsed.netloc != "localhost":
            raise ValueError("SQLite DATABASE_URL must point to a local file")

        path = unquote(parsed.path)
        if path.startswith("//"):
            path = f"/{path.lstrip('/')}"

        return Path(path).expanduser()

    return Path(environ.get("SQLITE_PATH", "/tmp/resy-bot-jobs.db")).expanduser()


class JobStore:
    def __init__(self) -> None:
        self._path = _database_path()
        self._lock = Lock()
        self.initialize()

    @property
    def path(self) -> Path:
        return self._path

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    reservation_token TEXT,
                    error TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_job(self, job_id: str, status: str, request: dict) -> None:
        timestamp = _now()
        request_json = json.dumps(request)

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id,
                    status,
                    request_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, status, request_json, timestamp, timestamp),
            )

    def get_job(self, job_id: str) -> StoredJob | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    status,
                    request_json,
                    reservation_token,
                    error,
                    cancel_requested,
                    created_at,
                    updated_at
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()

        return self._row_to_job(row) if row else None

    def list_jobs(self) -> list[StoredJob]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    status,
                    request_json,
                    reservation_token,
                    error,
                    cancel_requested,
                    created_at,
                    updated_at
                FROM jobs
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [self._row_to_job(row) for row in rows]

    def set_job(
        self,
        job_id: str,
        status: str,
        *,
        reservation_token: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET
                    status = ?,
                    reservation_token = ?,
                    error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (status, reservation_token, error, _now(), job_id),
            )

    def request_cancel(self, job_id: str, status: str, error: str) -> StoredJob | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

            if not row:
                return None

            conn.execute(
                """
                UPDATE jobs
                SET
                    status = ?,
                    error = ?,
                    cancel_requested = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (status, error, _now(), job_id),
            )

        return self.get_job(job_id)

    def mark_active_interrupted(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET
                    status = 'failed',
                    error = 'Backend restarted before this job finished',
                    updated_at = ?
                WHERE status IN ('pending', 'running', 'cancelling')
                """,
                (_now(),),
            )

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM jobs")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_job(self, row: sqlite3.Row) -> StoredJob:
        return StoredJob(
            id=row["id"],
            status=row["status"],
            request_json=row["request_json"],
            reservation_token=row["reservation_token"],
            error=row["error"],
            cancel_requested=bool(row["cancel_requested"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
