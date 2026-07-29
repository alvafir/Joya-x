from __future__ import annotations

from typing import Any

import requests
import streamlit as st


API_BASE_URL = "https://v3.football.api-sports.io"
TIMEOUT_SECONDS = 20


def _read_secret(name: str) -> str:
    value = st.secrets.get(name, "")
    return str(value).strip() if value is not None else ""


def get_secret_status() -> dict[str, bool]:
    return {
        "APISPORTS_KEY": bool(_read_secret("APISPORTS_KEY")),
        "FOOTBALL_DATA_API_KEY": bool(
            _read_secret("FOOTBALL_DATA_API_KEY")
        ),
        "THESPORTSDB_API_KEY": bool(
            _read_secret("THESPORTSDB_API_KEY")
        ),
    }


def _headers() -> dict[str, str]:
    api_key = _read_secret("APISPORTS_KEY")

    if not api_key:
        raise ValueError(
            "Falta APISPORTS_KEY en Streamlit Secrets."
        )

    return {
        "x-apisports-key": api_key,
    }


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}

    return payload if isinstance(payload, dict) else {}


def test_api_football_connection() -> dict[str, Any]:
    try:
        response = requests.get(
            f"{API_BASE_URL}/status",
            headers=_headers(),
            timeout=TIMEOUT_SECONDS,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "message": str(exc),
        }
    except requests.Timeout:
        return {
            "ok": False,
            "message": (
                "API-Football tardó demasiado en responder. "
                "Intenta nuevamente."
            ),
        }
    except requests.RequestException as exc:
        return {
            "ok": False,
            "message": f"Error de conexión: {exc}",
        }

    payload = _safe_json(response)

    if response.status_code != 200:
        api_errors = payload.get("errors") or {}
        return {
            "ok": False,
            "message": (
                f"API-Football respondió con código "
                f"{response.status_code}: {api_errors or 'Sin detalle'}"
            ),
        }

    api_errors = payload.get("errors") or {}

    if api_errors:
        return {
            "ok": False,
            "message": f"API-Football informó: {api_errors}",
        }

    results = payload.get("response") or {}
    requests_data = results.get("requests") or {}
    subscription = results.get("subscription") or {}
    account = results.get("account") or {}

    current = requests_data.get("current")
    limit_day = requests_data.get("limit_day")

    remaining = "No informado"

    if isinstance(current, int) and isinstance(limit_day, int):
        remaining = max(0, limit_day - current)

    return {
        "ok": True,
        "message": "Conexión correcta.",
        "requests_remaining": remaining,
        "plan": subscription.get("plan") or "No informado",
        "account": (
            account.get("firstname")
            or account.get("email")
            or ""
        ),
    }
