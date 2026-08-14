"""Small, dependency-free client for the FormFav internal racecard feed."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://api.formfav.com/v1"


class FormFavError(RuntimeError):
    """Raised when FormFav cannot provide a valid response."""


def load_key() -> str:
    """Read the key from the environment or the private local key file."""
    if key := os.environ.get("FORMFAV_API_KEY", "").strip():
        return key

    root = Path(__file__).resolve().parents[2]
    candidates = (
        root / ".env.formfav.local",
        root / "BettingEngine" / ".env.formfav.local",
    )
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("FORMFAV_API_KEY="):
                return line.partition("=")[2].strip()
    raise FormFavError(
        "FORMFAV_API_KEY is not available. Run BettingEngine/scripts/set_formfav_key.py first."
    )


class FormFavClient:
    def __init__(self, api_key: str | None = None, timeout_seconds: int = 30) -> None:
        self.api_key = api_key or load_key()
        self.timeout_seconds = timeout_seconds

    def _get(self, path: str, params: dict[str, str | int]) -> dict[str, Any]:
        url = f"{BASE_URL}{path}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "BetMate-RacingEngine/0.1 (internal data ingestion)",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise FormFavError(f"FormFav returned HTTP {error.code}: {body[:400]}") from error
        except URLError as error:
            raise FormFavError(f"Could not reach FormFav: {error.reason}") from error

    def meetings(self, race_date: str) -> dict[str, Any]:
        return self._get(
            "/form/meetings",
            {"date": race_date, "race_code": "gallops", "timezone": "Australia/Sydney"},
        )

    def race_form(self, race_date: str, track_slug: str, race_number: int) -> dict[str, Any]:
        return self._get(
            "/form",
            {
                "date": race_date,
                "track": track_slug,
                "race": race_number,
                "race_code": "gallops",
                "country": "au",
                "timezone": "Australia/Sydney",
            },
        )
