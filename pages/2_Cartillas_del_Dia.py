import os
from datetime import date

import pandas as pd
import streamlit as st

from modules.cache import cached_fixtures
from modules.scanner import fixtures_to_rows
from modules.global_scanner import scan_day
from modules.cartilla_builder import build_cartillas


st.set_page_config(
    page_title="Cartillas del Día · JOYA",
    page_icon="📋",
    layout="wide",
)


def get_api_key():
    try:
        return st.secrets.get("API_FOOTBALL_KEY")
    except Exception:
        return os.getenv("API_FOOTBALL_KEY")


st.title("📋 JOYA Cartillas del Día")
st.caption(
    "Mercados reales API-Football · Proyección JOYA · Ranking y cartillas automáticas"
)

api_key = get_api_key()
if not api_key:
    st.error("Configura API_FOOTBALL_KEY en Streamlit Secrets.")
    st.stop()

with st.sidebar:
    selected_date = st.date_input("Fecha", value=date.today())
    min_league_score = st.slider(
        "League Score mínimo",
        min_value=50,
        max_value=95,
        value=70,
    )
    max_matches = st.slider(
        "Máximo de partidos por ejecución",
        min_value=5,
        max_value=80,
        value=25,
        step=5,
    )
    min_edge = st.slider(
        "Edge mínimo global (%)",
        min_value=-10.0,
        max_value=20.0,
        value=0.0,
        step=0.5,
    )
    st.warning(
        "Cada partido puede requerir cuotas, predicción y forma reciente. "
        "A mayor cantidad, mayor consumo de solicitudes API."
    )

payload = cached_fixtures(api_key, selected_date.isoformat())
rows = fixtures_to_rows(payload)

if not rows:
    st.info("No se encontraron partidos para esta fecha.")
    st.stop()

countries = len({row.get("país") for row in rows if row.get("país")})
leagues = len({(row.get("país"), row.get("liga")) for row in rows})

c1, c2, c3 = st.columns(3)
c1.metric("Partidos disponibles", len(rows))
c2.metric("Países", countries)
c3.metric("Ligas", leagues)

if st.button(
    "🚀 Analizar ligas y crear cartillas",
    type="primary",
    use_container_width=True,
):
    progress = st.progress(0)
    status_box = st.empty()

    def update_progress(index, total, result):
        progress.progress(index / max(total, 1))
        status_box.caption(
            f"{index}/{total} · {result.home} vs {result.away} · {result.status}"
        )

    with st.spinner("JOYA está analizando los partidos del día..."):
        scanned = scan_day(
            api_key,
            rows,
            max_matches=max_matches,
            min_league_score=min_league_score,
            bookmaker_id=None,
            min_edge=min_edge,
            progress_callback=update_progress,
        )

    st.session_state["joya_scanned_day"] = scanned
    st.session_state["joya_cartillas_day"] = build_cartillas(scanned)
    status_box.success("Análisis global finalizado.")

scanned = st.session_state.get("joya_scanned_day")
cartillas = st.session_state.get("joya_cartillas_day")

if scanned:
    approved = sum(item.status == "APROBADO" for item in scanned)
    no_bet = sum(item.status == "NO BET" for item in scanned)
    errors = sum(item.status == "ERROR" for item in scanned)

    st.subheader("📊 Resumen del Scanner")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Analizados", len(scanned))
    r2.metric("Aprobados", approved)
    r3.metric("NO BET", no_bet)
    r4.metric("Errores", errors)

    with st.expander("Partidos analizados y descartados"):
        scan_df = pd.DataFrame([
            {
                "fixture_id": item.fixture_id,
                "country": item.country,
                "league": item.league,
                "match": f"{item.home} vs {item.away}",
                "league_score": item.league_score,
                "status": item.status,
                "reason": item.reason,
                "api_markets": item.api_market_count,
                "markets": len(item.markets),
                "discarded": len(item.discarded),
            }
            for item in scanned
        ])
        st.dataframe(scan_df, use_container_width=True, hide_index=True)

if cartillas:
    st.subheader("🏆 Cartillas Automáticas")

    tabs = st.tabs(list(cartillas.keys()))

    for tab, (name, picks) in zip(tabs, cartillas.items()):
        with tab:
            if not picks:
                st.info(
                    f"No existen picks suficientes para construir {name} "
                    "con los filtros actuales."
                )
                continue

            for index, pick in enumerate(picks, start=1):
                icon = "🟢" if pick.status == "BET" else "🟡"
                st.markdown(
                    f"""
                    **{index}. {icon} {pick.match}**

                    **Mercado:** {pick.market}  
                    **Liga:** {pick.league} · {pick.country}  
                    **Mercado API:** {pick.api_market} · {pick.api_selection}  
                    **Bookmaker:** {pick.bookmaker} · **Cuota:** {pick.odd:.2f}  
                    **JOYA Score:** {pick.joya_score:.1f}/100  
                    **Probabilidad JOYA:** {pick.probability:.1f}% ·
                    **Implícita:** {pick.implicit_probability:.1f}% ·
                    **Edge:** {pick.edge:+.1f}%  
                    **Confianza:** {pick.confidence:.1f}% ·
                    **Riesgo:** {pick.risk} · **Estado:** {pick.status}

                    _{pick.reason}_
                    """
                )
                st.divider()

            export_df = pd.DataFrame([pick.to_dict() for pick in picks])
            st.download_button(
                f"Descargar {name} en CSV",
                data=export_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=(
                    name.lower()
                    .replace(" ", "_")
                    .replace("+", "plus")
                    .replace("ú", "u")
                    .replace("ñ", "n")
                    + ".csv"
                ),
                mime="text/csv",
                key=f"download_{name}",
            )
