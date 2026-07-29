import os
from typing import Any, Dict, Optional
import requests

BASE_URL = "https://v3.football.api-sports.io"

class APIFootballError(RuntimeError):
    pass

class APIFootballClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 25):
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        self.timeout = timeout
        if not self.api_key:
            raise APIFootballError("Falta API_FOOTBALL_KEY.")

    @property
    def headers(self) -> Dict[str, str]:
        return {"x-apisports-key": self.api_key}

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{BASE_URL}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params or {},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise APIFootballError(f"Error de red/API: {exc}") from exc
        except ValueError as exc:
            raise APIFootballError("La API devolvió una respuesta no válida.") from exc

        if payload.get("errors"):
            raise APIFootballError(f"API-Football informó errores: {payload['errors']}")
        return payload

    def status(self) -> Dict[str, Any]:
        return self._get("status")

    def fixtures_by_date(self, date: str, timezone: str = "America/Santiago") -> Dict[str, Any]:
        return self._get("fixtures", {"date": date, "timezone": timezone})

    def prediction(self, fixture_id: int) -> Dict[str, Any]:
        return self._get("predictions", {"fixture": fixture_id})

    def recent_team_fixtures(self, team_id: int, last: int = 10) -> Dict[str, Any]:
        return self._get("fixtures", {"team": team_id, "last": last, "status": "FT"})

    def h2h(self, home_team_id: int, away_team_id: int, last: int = 10) -> Dict[str, Any]:
        return self._get("fixtures", {
            "h2h": f"{home_team_id}-{away_team_id}",
            "last": last,
            "status": "FT",
        })
