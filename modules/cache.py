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
