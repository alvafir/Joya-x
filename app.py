from datetime import date

import streamlit as st

from modules.api import (
    get_fixture_prediction,
    get_secret_status,
    test_api_football_connection,
)
from modules.league_intelligence import (
    enrich_league_summary,
    filter_leagues,
)
from modules.match_center import build_match_table
from modules.probability import parse_prediction
from modules.scanner import scan_fixtures

st.set_page_config(
    page_title="JOYA Enterprise 4.1",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 JOYA Enterprise 4.1")
st.caption("v4.1.0 DEV · League Intelligence + Match Center + Probability MVP")

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

        match_table = build_match_table(scan_result.get("fixtures", []))

        allowed_pairs = set(
            zip(
                filtered["País"].astype(str),
                filtered["Liga"].astype(str),
            )
        )

        if not match_table.empty:
            match_table = match_table[
                match_table.apply(
                    lambda row: (str(row["País"]), str(row["Liga"]))
                    in allowed_pairs,
                    axis=1,
                )
            ].reset_index(drop=True)

        st.divider()
        st.subheader("⚽ Match Center")

        if match_table.empty:
            st.info("No hay partidos disponibles con los filtros actuales.")
        else:
            countries = sorted(match_table["País"].unique().tolist())
            selected_country = st.selectbox(
                "País",
                countries,
            )

            country_matches = match_table[
                match_table["País"] == selected_country
            ]

            leagues = sorted(country_matches["Liga"].unique().tolist())
            selected_league = st.selectbox(
                "Liga",
                leagues,
            )

            league_matches = country_matches[
                country_matches["Liga"] == selected_league
            ].reset_index(drop=True)

            selected_match_name = st.selectbox(
                "Partido",
                league_matches["Partido"].tolist(),
            )

            selected_row = league_matches[
                league_matches["Partido"] == selected_match_name
            ].iloc[0]

            st.caption(
                f"{selected_row['Hora']} · Fixture ID "
                f"{int(selected_row['fixture_id'])}"
            )

            if st.button(
                "🧠 Ejecutar Probability MVP",
                use_container_width=True,
            ):
                with st.spinner("Consultando predicción disponible…"):
                    api_prediction = get_fixture_prediction(
                        int(selected_row["fixture_id"])
                    )

                if not api_prediction["ok"]:
                    st.warning(api_prediction["message"])
                else:
                    parsed = parse_prediction(api_prediction["data"])
                    st.session_state["probability_result"] = parsed
                    st.session_state["probability_match"] = selected_match_name

probability_result = st.session_state.get("probability_result")

if probability_result:
    st.divider()
    st.subheader("🧠 Probability MVP")
    st.caption(st.session_state.get("probability_match", ""))

    p1, p2, p3 = st.columns(3)

    p1.metric(
        probability_result.get("home_team") or "Local",
        (
            f"{probability_result['home_percent']}%"
            if probability_result.get("home_percent") is not None
            else "Sin dato"
        ),
    )

    p2.metric(
        "Empate",
        (
            f"{probability_result['draw_percent']}%"
            if probability_result.get("draw_percent") is not None
            else "Sin dato"
        ),
    )

    p3.metric(
        probability_result.get("away_team") or "Visitante",
        (
            f"{probability_result['away_percent']}%"
            if probability_result.get("away_percent") is not None
            else "Sin dato"
        ),
    )

    st.info(f"Consejo API-Football: {probability_result.get('advice')}")

    winner_comment = probability_result.get("winner_comment")

    if winner_comment:
        st.caption(winner_comment)

    st.warning(
        "Este es un MVP basado únicamente en la predicción disponible "
        "de API-Football. Todavía no incluye el modelo estadístico propio "
        "de JOYA ni debe tratarse como BET automático."
    )

st.divider()
st.info(
    "Versión DEV. No reemplaza la rama principal estable."
)
