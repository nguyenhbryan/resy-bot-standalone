import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from os import environ
from pathlib import Path
from threading import Lock
from typing import Any

from resy_bot.logging_config import logging


logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@dataclass(frozen=True)
class VenueCandidate:
    venue_id: str
    name: str
    locality: str | None = None
    region: str | None = None
    url_slug: str | None = None


def normalize_venue_text(value: str | None) -> str:
    if not value:
        return ""

    normalized = value.casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _venue_cache_path() -> Path:
    return Path(
        environ.get("RESY_VENUE_CACHE_PATH", "/tmp/resy-bot-venues.db")
    ).expanduser()


def _now() -> str:
    return datetime.now(UTC).isoformat()


class VenueCache:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _venue_cache_path()
        self._lock = Lock()
        self.initialize()

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS venues (
                    venue_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    locality TEXT,
                    region TEXT,
                    normalized_location TEXT,
                    url_slug TEXT,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS venues_normalized_lookup
                ON venues (normalized_name, normalized_location)
                """
            )

    def upsert(self, candidate: VenueCandidate) -> None:
        normalized_location = normalize_venue_text(
            " ".join(
                part
                for part in (candidate.locality, candidate.region)
                if part
            )
        )

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO venues (
                    venue_id,
                    name,
                    normalized_name,
                    locality,
                    region,
                    normalized_location,
                    url_slug,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(venue_id) DO UPDATE SET
                    name = excluded.name,
                    normalized_name = excluded.normalized_name,
                    locality = excluded.locality,
                    region = excluded.region,
                    normalized_location = excluded.normalized_location,
                    url_slug = excluded.url_slug,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    candidate.venue_id,
                    candidate.name,
                    normalize_venue_text(candidate.name),
                    candidate.locality,
                    candidate.region,
                    normalized_location or None,
                    candidate.url_slug,
                    _now(),
                ),
            )

    def find(self, name: str, location: str | None = None) -> VenueCandidate | None:
        normalized_name = normalize_venue_text(name)
        normalized_location = normalize_venue_text(location)

        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT venue_id, name, locality, region, url_slug, normalized_location
                FROM venues
                WHERE normalized_name = ?
                """,
                (normalized_name,),
            ).fetchall()

        if not rows:
            return None

        if normalized_location:
            rows = [
                row
                for row in rows
                if normalized_location
                and normalized_location in (row["normalized_location"] or "")
            ]

        if len(rows) != 1:
            return None

        return self._row_to_candidate(rows[0])

    def find_fuzzy(
        self, name: str, location: str | None = None
    ) -> VenueCandidate | None:
        normalized_name = normalize_venue_text(name)
        normalized_location = normalize_venue_text(location)

        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    venue_id,
                    name,
                    locality,
                    region,
                    url_slug,
                    normalized_name,
                    normalized_location
                FROM venues
                """
            ).fetchall()

        scored = []
        for row in rows:
            if normalized_location and normalized_location not in (
                row["normalized_location"] or ""
            ):
                continue

            score = SequenceMatcher(
                None, normalized_name, row["normalized_name"]
            ).ratio()

            if score >= 0.88:
                scored.append((score, row))

        if not scored:
            return None

        scored.sort(key=lambda item: item[0], reverse=True)

        if len(scored) > 1 and scored[0][0] == scored[1][0]:
            return None

        return self._row_to_candidate(scored[0][1])

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM venues")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_candidate(self, row: sqlite3.Row) -> VenueCandidate:
        return VenueCandidate(
            venue_id=row["venue_id"],
            name=row["name"],
            locality=row["locality"],
            region=row["region"],
            url_slug=row["url_slug"],
        )


class VenueResolver:
    def __init__(self, api_access: Any, cache: VenueCache | None = None) -> None:
        self.api_access = api_access
        self.cache = cache or VenueCache()

    def resolve(self, name: str, location: str | None = None) -> str:
        return self.resolve_candidate(name, location).venue_id

    def resolve_candidate(
        self, name: str, location: str | None = None
    ) -> VenueCandidate:
        cached = self.cache.find(name, location) or self.cache.find_fuzzy(
            name, location
        )

        if cached:
            logger.info("Resolved venue %s from cache as %s", name, cached.venue_id)
            return cached

        candidates = self.api_access.search_venues(name, location)

        if not candidates:
            raise ValueError(f"No Resy venue found for {name}")

        matches = self._rank_candidates(name, location, candidates)

        if not matches:
            raise ValueError(f"No Resy venue found for {name}")

        if len(matches) > 1 and matches[0][0] == matches[1][0]:
            descriptions = ", ".join(
                self._describe_candidate(candidate) for _, candidate in matches[:5]
            )
            raise ValueError(
                f"Multiple Resy venues matched {name}. Add a city or use venue_id. "
                f"Candidates: {descriptions}"
            )

        candidate = matches[0][1]
        config_candidate = self.api_access.get_venue_config(candidate.venue_id)

        if config_candidate:
            candidate = VenueCandidate(
                venue_id=candidate.venue_id,
                name=config_candidate.name or candidate.name,
                locality=config_candidate.locality or candidate.locality,
                region=config_candidate.region or candidate.region,
                url_slug=config_candidate.url_slug or candidate.url_slug,
            )

        self.cache.upsert(candidate)
        logger.info("Resolved venue %s from Resy as %s", name, candidate.venue_id)
        return candidate

    def _rank_candidates(
        self,
        name: str,
        location: str | None,
        candidates: list[VenueCandidate],
    ) -> list[tuple[float, VenueCandidate]]:
        normalized_name = normalize_venue_text(name)
        normalized_location = normalize_venue_text(location)
        matches = []

        for candidate in candidates:
            score = SequenceMatcher(
                None, normalized_name, normalize_venue_text(candidate.name)
            ).ratio()

            candidate_location = normalize_venue_text(
                " ".join(
                    part
                    for part in (candidate.locality, candidate.region)
                    if part
                )
            )

            if normalized_name == normalize_venue_text(candidate.name):
                score += 0.25

            if normalized_location:
                if normalized_location in candidate_location:
                    score += 0.2
                else:
                    score -= 0.2

            if score >= 0.75:
                matches.append((score, candidate))

        matches.sort(key=lambda item: item[0], reverse=True)
        return matches

    def _describe_candidate(self, candidate: VenueCandidate) -> str:
        location = ", ".join(
            part for part in (candidate.locality, candidate.region) if part
        )
        if location:
            return f"{candidate.name} ({location}, id {candidate.venue_id})"

        return f"{candidate.name} (id {candidate.venue_id})"
