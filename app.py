from datetime import date

import streamlit as st

from modules.api import get_secret_status, test_api_football_connection
from modules.scanner import scan_fixtures
from modules.league_intelligence import (
    enrich_league_summary,
    filter_leagues,
)

st.set_page_config(
    page_title="JOYA Enterprise 4.0",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 JOYA Enterprise 4.0")
st.caption("v4.0.3 · League Intelligence Center")

secret_status = get_secret_status()

with st.sidebar:
    st.header("Filtros")
    recommended_only = st.checkbox("Solo ligas recomendadas", value=False)
    exclude_friendlies = st.checkbox("Excluir amistosos", value=True)
    exclude_youth = st.checkbox("Excluir juveniles y reservas", value=True)
    minimum_matches = st.slider(
        "Mínimo de partidos",
        min_value=1,
        max_value=10,
        value=1,
    )

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
    st.subheader("🌍 League Intelligence")

    scan_date = st.date_input(
        "Fecha",
        value=date.today(),
        format="YYYY-MM-DD",
    )

    if st.button(
        "Escanear y clasificar ligas",
        use_container_width=True,
    ):
        with st.spinner("Escaneando partidos y evaluando ligas…"):
            scan_result = scan_fixtures(scan_date.isoformat())

        if not scan_result["ok"]:
            st.error(scan_result["message"])
        else:
            scan_result["intelligence"] = enrich_league_summary(
                scan_result["summary"]
            )
            st.session_state["scan_result"] = scan_result

scan_result = st.session_state.get("scan_result")

if scan_result:
    intelligence = scan_result.get("intelligence")

    if intelligence is None:
        intelligence = enrich_league_summary(scan_result["summary"])

    filtered = filter_leagues(
        intelligence,
        recommended_only=recommended_only,
        exclude_friendlies=exclude_friendlies,
        exclude_youth=exclude_youth,
        minimum_matches=minimum_matches,
    )

    st.divider()
    st.subheader("🌍 League Intelligence Center")

    m1, m2, m3 = st.columns(3)
    m1.metric("Partidos encontrados", scan_result["total"])
    m2.metric("Ligas detectadas", len(intelligence))
    m3.metric(
        "Ligas recomendadas",
        int((intelligence["League Score"] >= 85).sum())
        if not intelligence.empty
        else 0,
    )

    if filtered.empty:
        st.info("No hay ligas que cumplan los filtros seleccionados.")
    else:
        st.dataframe(
            filtered[
                [
                    "País",
                    "Liga",
                    "Partidos",
                    "Cobertura",
                    "League Score",
                    "Estado",
                    "Prioridad",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Top ligas por calidad")

        top = filtered.head(10)

        for _, row in top.iterrows():
            with st.container(border=True):
                a, b, c = st.columns([3, 1, 1])

                a.markdown(
                    f"### {row['País']} · {row['Liga']}"
                )
                a.caption(
                    f"{int(row['Partidos'])} partidos · {row['Cobertura']}"
                )
                b.metric("League Score", int(row["League Score"]))
                c.metric("Estado", row["Prioridad"])

                st.progress(int(row["League Score"]) / 100)

st.divider()
st.info(
    "Cuando League Intelligence quede validado, "
    "el siguiente paso será incorporar el caché."
)
