import os
from datetime import date
import pandas as pd
import streamlit as st

from modules.api import APIFootballError
from modules.cache import cached_fixtures, cached_prediction, cached_status
from modules.data_quality import evaluate_data_quality
from modules.projection import build_projection
from modules.scanner import fixtures_to_rows
from modules.winner_engine import evaluate_winner_markets

st.set_page_config(
    page_title="JOYA Enterprise 4.4",
    page_icon="💎",
    layout="wide",
)

st.markdown("""
<style>
.stApp {background: #0b0f14;}
.block-container {padding-top: 1.2rem;}
.joya-card {
  border: 1px solid #3d3218;
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(145deg,#121821,#0d1218);
  margin-bottom: 12px;
}
.joya-title {color:#d9b44a;font-weight:800;letter-spacing:.04em;}
.small-muted {color:#9aa4b2;font-size:.88rem;}
</style>
""", unsafe_allow_html=True)

def get_api_key():
    try:
        return st.secrets.get("API_FOOTBALL_KEY")
    except Exception:
        return os.getenv("API_FOOTBALL_KEY")

def league_score_for_fixture(row):
    # Valor inicial explícito y editable. No pretende reemplazar League Intelligence.
    default = 80
    country = (row.get("país") or "").lower()
    league = (row.get("liga") or "").lower()
    if "friendly" in league or "amistoso" in league:
        default = 62
    if any(x in league for x in ("u17", "u18", "u19", "u20", "u21", "youth", "reserve")):
        default = min(default, 58)
    return default

st.markdown("<h1 class='joya-title'>💎 JOYA Enterprise 4.4 DEV</h1>", unsafe_allow_html=True)
st.caption("Data Quality + Projection Engine + Winner Engine")

api_key = get_api_key()
if not api_key:
    st.error("Configura API_FOOTBALL_KEY en Streamlit Secrets.")
    st.stop()

with st.sidebar:
    st.header("API Manager")
    try:
        status_payload = cached_status(api_key)
        account = (status_payload.get("response") or {}).get("account") or {}
        subscription = (status_payload.get("response") or {}).get("subscription") or {}
        requests_info = (status_payload.get("response") or {}).get("requests") or {}
        st.success("API-Football conectada")
        st.write("Cuenta:", account.get("firstname") or account.get("email") or "OK")
        st.write("Plan:", subscription.get("plan") or "—")
        st.write("Solicitudes restantes:", requests_info.get("limit_day", "—"))
    except Exception as exc:
        st.warning(f"No fue posible leer el estado: {exc}")

    selected_date = st.date_input("Fecha", value=date.today())
    min_score = st.slider("League Score mínimo", 40, 100, 70)

try:
    fixtures_payload = cached_fixtures(api_key, selected_date.isoformat())
except APIFootballError as exc:
    st.error(str(exc))
    st.stop()

rows = fixtures_to_rows(fixtures_payload)
if not rows:
    st.info("No se encontraron partidos para la fecha seleccionada.")
    st.stop()

countries = sorted({r["país"] for r in rows if r["país"]})
country = st.selectbox("País", countries)
country_rows = [r for r in rows if r["país"] == country]

leagues = sorted({r["liga"] for r in country_rows if r["liga"]})
league = st.selectbox("Liga", leagues)
league_rows = [r for r in country_rows if r["liga"] == league]

labels = {f'{r["partido"]} · ID {r["fixture_id"]}': r for r in league_rows}
selected_label = st.selectbox("Partido", list(labels.keys()))
selected = labels[selected_label]
league_score = league_score_for_fixture(selected)

c1, c2, c3 = st.columns(3)
c1.metric("Partidos del día", len(rows))
c2.metric("League Score", league_score)
c3.metric("Filtro mínimo", min_score)

if league_score < min_score:
    st.error("🔴 NO BET: la liga no supera el filtro configurado.")
    st.stop()

if st.button("🧠 Ejecutar análisis JOYA", type="primary", use_container_width=True):
    with st.spinner("Consultando predicción y ejecutando motores..."):
        try:
            prediction_payload = cached_prediction(api_key, int(selected["fixture_id"]))
            quality = evaluate_data_quality(
                selected["raw"], prediction_payload, league_score=league_score
            )
        except Exception as exc:
            st.error(f"No fue posible ejecutar el análisis: {exc}")
            st.stop()

    st.subheader("📊 Data Quality Engine")
    q1, q2, q3 = st.columns(3)
    q1.metric("Data Quality", f"{quality.score:.0f}/100")
    q2.metric("Estado", quality.status)
    q3.metric("Muestra", quality.sample_quality)

    with st.expander("Controles de calidad"):
        st.json(quality.to_dict())

    if not quality.approved:
        st.error("🔴 NO BET — Datos insuficientes. Los motores quedaron bloqueados.")
        st.stop()

    try:
        projection = build_projection(prediction_payload, quality.score)
    except Exception as exc:
        st.error(f"No fue posible construir la proyección: {exc}")
        st.stop()

    st.subheader("📈 Projection Engine")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Marcador central", projection.expected_score)
    p2.metric("Goles esperados", projection.expected_goals)
    p3.metric("Marca primero", projection.first_goal_team)
    p4.metric("Confianza", f"{projection.projection_confidence:.0f}%")

    st.markdown(
        f"""<div class="joya-card">
        <div class="joya-title">Guion proyectado</div>
        <div>{projection.match_script}</div>
        <div class="small-muted">Ventana probable del primer gol: {projection.first_goal_window}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Sin gol antes 10", f"{projection.no_goal_before_10:.1f}%")
    t2.metric("Sin gol antes 20", f"{projection.no_goal_before_20:.1f}%")
    t3.metric("Gol antes 70", f"{projection.goal_before_70:.1f}%")
    t4.metric("Gol antes 80", f"{projection.goal_before_80:.1f}%")

    if projection.warnings:
        for warning in projection.warnings:
            st.warning(warning)

    decisions = evaluate_winner_markets(projection, quality, league_score)
    data = [d.to_dict() for d in decisions]

    st.subheader("🏆 Winner Engine")
    df = pd.DataFrame(data)
    st.dataframe(
        df[[
            "market", "probability", "confidence", "risk",
            "joya_score", "status", "reason"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    valid = [d for d in decisions if d.status != "NO BET"]
    st.subheader("💎 Ranking JOYA")
    if not valid:
        st.error("No existe un mercado Winner aprobado para este partido.")
    else:
        for idx, item in enumerate(valid[:5], start=1):
            icon = "🟢" if item.status == "BET" else "🟡"
            st.markdown(
                f"""<div class="joya-card">
                <div class="joya-title">{idx}. {icon} {item.market}</div>
                <b>JOYA SCORE:</b> {item.joya_score}/100 ·
                <b>Probabilidad:</b> {item.probability}% ·
                <b>Riesgo:</b> {item.risk} ·
                <b>Estado:</b> {item.status}
                <div class="small-muted">{item.reason}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    with st.expander("Salida técnica completa"):
        st.json({
            "fixture": {
                "id": selected["fixture_id"],
                "home": selected["local"],
                "away": selected["visitante"],
                "league": selected["liga"],
            },
            "data_quality": quality.to_dict(),
            "projection": projection.to_dict(),
            "winner_markets": data,
        })
