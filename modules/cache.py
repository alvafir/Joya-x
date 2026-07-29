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
