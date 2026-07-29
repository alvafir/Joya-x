import streamlit as st

from modules.api import get_secret_status, test_api_football_connection

st.set_page_config(
    page_title="JOYA Enterprise 4.0",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 JOYA Enterprise 4.0")
st.caption("v4.0.1 · Sprint 1 · API Manager")

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

if st.button(
    "🔌 Probar conexión API-Football",
    type="primary",
    use_container_width=True,
):
    with st.spinner("Probando conexión con API-Football…"):
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

        if result.get("account"):
            st.caption(f"Cuenta: {result['account']}")
    else:
        st.error(result["message"])

st.divider()

st.subheader("Siguiente módulo")
st.info(
    "Cuando la conexión API-Football quede en verde, "
    "el siguiente paso será activar el Scanner de partidos."
)
