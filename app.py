from datetime import date

import streamlit as st

from modules.api import get_secret_status, test_api_football_connection
from modules.scanner import scan_fixtures

st.set_page_config(
    page_title="JOYA Enterprise 4.0",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 JOYA Enterprise 4.0")
st.caption("v4.0.2 · Sprint 1 · API Manager + Scanner")

secret_status = get_secret_status()

st.subheader("Estado del sistema")

c1, c2, c3 = st.columns(3)
c1.metric(
    "API-Football",
    "Configurada" if secret_status["APISPORTS_KEY"] else "Sin clave",
)
c2.metric(
    "Football Data",
    "Configurada" if secret_status["FOOTBALL_DATA_API_KEY"] else "Sin clave",
)
c3.metric(
    "TheSportsDB",
    "Configurada" if secret_status["THESPORTSDB_API_KEY"] else "Sin clave",
)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("🔌 API Manager")

    if st.button(
        "Probar conexión API-Football",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Probando conexión…"):
            result = test_api_football_connection()

        if result["ok"]:
            st.success("API-Football conectada correctamente.")
            r1, r2, r3 = st.columns(3)
            r1.metric("Estado", "Conectada")
            r2.metric("Plan", result.get("plan", "No informado"))
            r3.metric(
                "Solicitudes restantes",
                result.get("requests_remaining", "No informado"),
            )
        else:
            st.error(result["message"])

with right:
    st.subheader("🔍 Scanner")

    scan_date = st.date_input(
        "Fecha",
        value=date.today(),
        format="YYYY-MM-DD",
    )

    if st.button(
        "Escanear partidos",
        use_container_width=True,
    ):
        with st.spinner("Buscando partidos…"):
            scan_result = scan_fixtures(scan_date.isoformat())

        if not scan_result["ok"]:
            st.error(scan_result["message"])
        else:
            st.session_state["scan_result"] = scan_result

scan_result = st.session_state.get("scan_result")

if scan_result:
    st.divider()
    st.subheader("Resultados del Scanner")

    m1, m2 = st.columns(2)
    m1.metric("Partidos encontrados", scan_result["total"])
    m2.metric(
        "Ligas encontradas",
        0 if scan_result["summary"].empty else len(scan_result["summary"]),
    )

    if scan_result["summary"].empty:
        st.info("No se encontraron partidos para esa fecha.")
    else:
        st.dataframe(
            scan_result["summary"],
            use_container_width=True,
            hide_index=True,
        )

st.divider()
st.info(
    "Cuando el Scanner quede validado, el siguiente paso será activar el caché."
)
