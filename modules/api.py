import os
import time
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://v3.football.api-sports.io"


class APIFootballError(RuntimeError):
    pass


class APIFootballClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 25,
        retries: int = 2,
    ):
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        self.timeout = timeout
        self.retries = max(0, retries)

        if not self.api_key:
            raise APIFootballError("Falta API_FOOTBALL_KEY.")

    @property
    def headers(self) -> Dict[str, str]:
        return {"x-apisports-key": self.api_key}

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        last_error: Optional[Exception] = None

        for attempt in range(self.retries + 1):
            try:
                response = requests.get(
                    f"{BASE_URL}/{endpoint.lstrip('/')}",
                    headers=self.headers,
                    params=params or {},
                    timeout=self.timeout,
                )

                if response.status_code >= 500:
                    raise requests.HTTPError(
                        f"Servidor API-Football: HTTP {response.status_code}"
                    )

                response.raise_for_status()
                payload = response.json()

                errors = payload.get("errors")
                if errors:
                    raise APIFootballError(
                        f"API-Football informó errores: {errors}"
                    )

                return payload

            except APIFootballError:
                raise
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue

        raise APIFootballError(
            f"No fue posible completar la consulta: {last_error}"
        )

    def status(self) -> Dict[str, Any]:
        return self._get("status")

    def fixtures_by_date(
        self,
        date: str,
        timezone: str = "America/Santiago",
    ) -> Dict[str, Any]:
        return self._get(
            "fixtures",
            {"date": date, "timezone": timezone},
        )

    def prediction(self, fixture_id: int) -> Dict[str, Any]:
        return self._get("predictions", {"fixture": fixture_id})

    def recent_team_fixtures(
        self,
        team_id: int,
        last: int = 10,
    ) -> Dict[str, Any]:
        return self._get(
            "fixtures",
            {"team": team_id, "last": last, "status": "FT"},
        )

    def h2h(
        self,
        home_team_id: int,
        away_team_id: int,
        last: int = 10,
    ) -> Dict[str, Any]:
        return self._get(
            "fixtures",
            {
                "h2h": f"{home_team_id}-{away_team_id}",
                "last": last,
            },
        )

    def fixture_statistics(self, fixture_id: int) -> Dict[str, Any]:
        return self._get(
            "fixtures/statistics",
            {"fixture": fixture_id},
        )

    def fixture_events(self, fixture_id: int) -> Dict[str, Any]:
        return self._get(
            "fixtures/events",
            {"fixture": fixture_id},
        )

    def odds_by_fixture(
        self,
        fixture_id: int,
        bookmaker: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"fixture": fixture_id}
        if bookmaker is not None:
            params["bookmaker"] = bookmaker
        return self._get("odds", params)

    def bookmakers(self) -> Dict[str, Any]:
        return self._get("odds/bookmakers")

    def bets_catalog(self) -> Dict[str, Any]:
        return self._get("odds/bets")
