import os
from datetime import date

import pandas as pd
import streamlit as st

from modules.cache import (
    cached_fixtures,
    cached_odds_by_fixture_safe,
    cached_bookmakers_safe,
    cached_bets_catalog_safe,
)
from modules.scanner import fixtures_to_rows
from modules.market_discovery import discover_markets, best_price


st.set_page_config(
    page_title="API Market Discovery · JOYA",
    page_icon="🔎",
    layout="wide",
)


def get_api_key():
    try:
        return st.secrets.get("API_FOOTBALL_KEY")
    except Exception:
        return os.getenv("API_FOOTBALL_KEY")


st.title("🔎 API Market Discovery")
st.caption(
    "Descubre únicamente los mercados y cuotas que API-Football ofrece para cada partido."
)

api_key = get_api_key()
if not api_key:
    st.error("Configura API_FOOTBALL_KEY en Streamlit Secrets.")
    st.stop()

selected_date = st.date_input("Fecha", value=date.today())
fixtures_payload = cached_fixtures(api_key, selected_date.isoformat())
rows = fixtures_to_rows(fixtures_payload)

if not rows:
    st.info("No se encontraron partidos.")
    st.stop()

countries = sorted({r["país"] for r in rows if r["país"]})
country = st.selectbox("País", countries)
country_rows = [r for r in rows if r["país"] == country]

leagues = sorted({r["liga"] for r in country_rows if r["liga"]})
league = st.selectbox("Liga", leagues)
league_rows = [r for r in country_rows if r["liga"] == league]

labels = {
    f'{r["partido"]} · ID {r["fixture_id"]}': r
    for r in league_rows
}
selected = labels[st.selectbox("Partido", list(labels.keys()))]

if st.button("Consultar mercados API", type="primary", use_container_width=True):
    result = cached_odds_by_fixture_safe(
        api_key,
        int(selected["fixture_id"]),
        None,
    )

    options = best_price(
        discover_markets(
            int(selected["fixture_id"]),
            result.get("payload") or {"response": []},
        )
    )

    st.session_state["api_market_options"] = options
    st.session_state["api_market_warning"] = result.get("warning")

warning = st.session_state.get("api_market_warning")
if warning:
    st.warning(warning)

options = st.session_state.get("api_market_options")
if options is not None:
    if not options:
        st.info("API-Football no entregó mercados/cuotas para este partido.")
    else:
        df = pd.DataFrame([option.to_dict() for option in options])

        m1, m2, m3 = st.columns(3)
        m1.metric("Opciones disponibles", len(df))
        m2.metric("Familias", df["family"].nunique())
        m3.metric("Bookmakers", df["bookmaker"].nunique())

        families = ["Todas"] + sorted(df["family"].unique().tolist())
        selected_family = st.selectbox("Filtrar familia", families)

        filtered = df
        if selected_family != "Todas":
            filtered = filtered[filtered["family"] == selected_family]

        st.dataframe(
            filtered[
                [
                    "family",
                    "normalized_market",
                    "api_market",
                    "selection",
                    "line",
                    "odd",
                    "bookmaker",
                    "updated_at",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
