from datetime import datetime
from requests import Session, HTTPError
from typing import Any, Dict, List

from resy_bot.constants import RESY_BASE_URL, ResyEndpoints
from resy_bot.logging_config import logging
from resy_bot.models import (
    ResyConfig,
    AuthRequestBody,
    AuthResponseBody,
    FindRequestBody,
    FindResponseBody,
    Slot,
    DetailsRequestBody,
    DetailsResponseBody,
    BookRequestBody,
    BookResponseBody,
)
from resy_bot.venue_resolver import VenueCandidate

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def build_session(config: ResyConfig) -> Session:
    session = Session()
    headers = {
        "Authorization": config.get_authorization(),
        "X-Resy-Auth-Token": config.token,
        "X-Resy-Universal-Auth": config.token,
        "Origin": "https://resy.com",
        "X-origin": "https://resy.com",
        "Referrer": "https://resy.com/",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Cache-Control": "no-cache",
    }

    session.headers.update(headers)

    return session


class ResyApiAccess:
    @classmethod
    def build(cls, config: ResyConfig) -> "ResyApiAccess":
        session = build_session(config)
        return cls(session)

    def __init__(self, session: Session):
        self.session = session

    def search_venues(
        self, query: str, location: str | None = None
    ) -> list[VenueCandidate]:
        search_url = RESY_BASE_URL + ResyEndpoints.VENUE_SEARCH.value
        search_query = f"{query} {location}".strip() if location else query
        payload = {"query": search_query, "per_page": 10}

        resp = self.session.post(search_url, json=payload)

        if resp.status_code in {400, 404, 405, 415}:
            resp = self.session.post(search_url, data=payload)

        if not resp.ok:
            raise HTTPError(
                f"Failed to search venues: {resp.status_code}, {resp.text}"
            )

        return self._extract_venue_candidates(resp.json())

    def get_venue_config(self, venue_id: str) -> VenueCandidate | None:
        config_url = RESY_BASE_URL + ResyEndpoints.VENUE_CONFIG.value

        resp = self.session.get(config_url, params={"venue_id": venue_id})

        if not resp.ok:
            raise HTTPError(
                f"Failed to get venue config: {resp.status_code}, {resp.text}"
            )

        candidates = self._extract_venue_candidates(resp.json())

        if candidates:
            candidate = candidates[0]
            return VenueCandidate(
                venue_id=venue_id,
                name=candidate.name,
                locality=candidate.locality,
                region=candidate.region,
                url_slug=candidate.url_slug,
            )

        return None

    def auth(self, body: AuthRequestBody) -> AuthResponseBody:
        auth_url = RESY_BASE_URL + ResyEndpoints.PASSWORD_AUTH.value

        resp = self.session.post(
            auth_url,
            data=body.dict(),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        if not resp.ok:
            raise HTTPError(f"Failed to get auth: {resp.status_code}, {resp.text}")

        return AuthResponseBody(**resp.json())

    def find_booking_slots(self, params: FindRequestBody) -> List[Slot]:
        find_url = RESY_BASE_URL + ResyEndpoints.FIND.value

        logger.info(
            f"{datetime.now().isoformat()} Sending request to find booking slots"
        )

        resp = self.session.get(find_url, params=params.dict())

        logger.info(f"{datetime.now().isoformat()} Received response for ")

        if not resp.ok:
            raise HTTPError(
                f"Failed to find booking slots: {resp.status_code}, {resp.text}"
            )

        parsed_resp = FindResponseBody(**resp.json())

        if parsed_resp.results.venues:
            slots = parsed_resp.results.venues[0].slots
            logger.info(f"Available slots: {[slot.date.start for slot in slots]}")
            return slots
        else:
            logger.info("No venues returned in response.")
            return []

    def get_booking_token(self, params: DetailsRequestBody) -> DetailsResponseBody:
        details_url = RESY_BASE_URL + ResyEndpoints.DETAILS.value

        resp = self.session.get(details_url, params=params.dict())

        if not resp.ok:
            raise HTTPError(
                f"Failed to get selected slot details: {resp.status_code}, {resp.text}"
            )

        return DetailsResponseBody(**resp.json())

    def _dump_book_request_body_to_dict(self, body: BookRequestBody) -> Dict:
        """
        requests lib doesn't urlencode nested dictionaries,
        so dump struct_payment_method to json and slot that in the dict
        """
        payment_method = body.struct_payment_method.json().replace(" ", "")
        body_dict = body.dict()
        body_dict["struct_payment_method"] = payment_method
        return body_dict

    def book_slot(self, body: BookRequestBody) -> str:
        book_url = RESY_BASE_URL + ResyEndpoints.BOOK.value

        body_dict = self._dump_book_request_body_to_dict(body)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://widgets.resy.com",
            "X-Origin": "https://widgets.resy.com",
            "Referrer": "https://widgets.resy.com/",
            "Cache-Control": "no-cache",
        }

        resp = self.session.post(
            book_url,
            data=body_dict,
            headers=headers,
        )

        if not resp.ok:
            raise HTTPError(f"Failed to book slot: {resp.status_code}, {resp.text}")

        logger.info(resp.json())
        parsed_resp = BookResponseBody(**resp.json())

        return parsed_resp.resy_token

    def _extract_venue_candidates(self, payload: Any) -> list[VenueCandidate]:
        candidates = []

        for item in self._walk_dicts(payload):
            candidate = self._dict_to_venue_candidate(item)

            if candidate and candidate not in candidates:
                candidates.append(candidate)

        return candidates

    def _walk_dicts(self, value: Any) -> list[dict]:
        if isinstance(value, dict):
            items = [value]
            for child in value.values():
                items.extend(self._walk_dicts(child))
            return items

        if isinstance(value, list):
            items = []
            for child in value:
                items.extend(self._walk_dicts(child))
            return items

        return []

    def _dict_to_venue_candidate(self, item: dict) -> VenueCandidate | None:
        venue_id = self._extract_venue_id(item)
        name = (
            item.get("name")
            or item.get("venue_name")
            or item.get("display_name")
        )

        if not venue_id or not name:
            return None

        locality = (
            item.get("locality")
            or item.get("city")
            or item.get("neighborhood")
        )
        region = (
            item.get("region")
            or item.get("state")
            or item.get("country")
        )
        url_slug = item.get("url_slug") or item.get("slug")

        return VenueCandidate(
            venue_id=str(venue_id),
            name=str(name),
            locality=str(locality) if locality else None,
            region=str(region) if region else None,
            url_slug=str(url_slug) if url_slug else None,
        )

    def _extract_venue_id(self, item: dict) -> str | int | None:
        raw_id = (
            item.get("venue_id")
            or item.get("resy_venue_id")
            or item.get("entity_id")
            or item.get("id")
        )

        if isinstance(raw_id, dict):
            raw_id = (
                raw_id.get("resy")
                or raw_id.get("venue_id")
                or raw_id.get("id")
            )

        return raw_id
