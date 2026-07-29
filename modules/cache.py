import streamlit as st

from .api import APIFootballClient


@st.cache_data(ttl=900, show_spinner=False)
def cached_status(api_key: str):
    return APIFootballClient(api_key).status()


@st.cache_data(ttl=600, show_spinner=False)
def cached_fixtures(api_key: str, date: str):
    return APIFootballClient(api_key).fixtures_by_date(date)


@st.cache_data(ttl=900, show_spinner=False)
def cached_prediction(api_key: str, fixture_id: int):
    return APIFootballClient(api_key).prediction(fixture_id)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_recent_team(api_key: str, team_id: int, last: int = 10):
    return APIFootballClient(api_key).recent_team_fixtures(team_id, last)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_h2h_safe(
    api_key: str,
    home_team_id: int,
    away_team_id: int,
    last: int = 10,
):
    try:
        payload = APIFootballClient(api_key).h2h(
            home_team_id,
            away_team_id,
            last,
        )
        return {
            "ok": True,
            "payload": payload,
            "warning": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "payload": {"response": []},
            "warning": f"H2H no disponible: {exc}",
        }


@st.cache_data(ttl=1800, show_spinner=False)
def cached_fixture_statistics_safe(api_key: str, fixture_id: int):
    try:
        payload = APIFootballClient(api_key).fixture_statistics(fixture_id)
        return {"ok": True, "payload": payload, "warning": None}
    except Exception as exc:
        return {
            "ok": False,
            "payload": {"response": []},
            "warning": f"Estadísticas fixture {fixture_id} no disponibles: {exc}",
        }


def cached_recent_statistics_batch(
    api_key: str,
    fixtures_payload,
    limit: int = 8,
):
    rows = (fixtures_payload or {}).get("response") or []
    results = []
    warnings = []

    for row in rows[:limit]:
        fixture_id = ((row.get("fixture") or {}).get("id"))
        if not fixture_id:
            continue
        item = cached_fixture_statistics_safe(api_key, int(fixture_id))
        if item["ok"]:
            results.append({
                "fixture": row,
                "statistics": item["payload"],
            })
        elif item.get("warning"):
            warnings.append(item["warning"])

    return {
        "items": results,
        "warnings": warnings,
        "requested": min(len(rows), limit),
        "available": len(results),
    }
