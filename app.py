import os
from datetime import date
import pandas as pd
import streamlit as st

from modules.api import APIFootballError
from modules.cache import cached_fixtures, cached_prediction, cached_status
from modules.data_quality import evaluate_data_quality
from modules.projection import build_projection
from modules.scanner import fixtures_to_rows
from modules.market_orchestrator import evaluate_all, global_ranking
from modules.joya_score import tier

st.set_page_config(page_title="JOYA Enterprise 4.5", page_icon="💎", layout="wide")

st.markdown("""
<style>
.stApp {background:#0b0f14;}
.block-container {padding-top:1.1rem;}
.joya-card {border:1px solid #3d3218;border-radius:16px;padding:16px;
background:linear-gradient(145deg,#121821,#0d1218);margin-bottom:10px}
.joya-title {color:#d9b44a;font-weight:800}
.small-muted {color:#9aa4b2;font-size:.87rem}
</style>
""", unsafe_allow_html=True)

def get_api_key():
    try:
        return st.secrets.get("API_FOOTBALL_KEY")
    except Exception:
        return os.getenv("API_FOOTBALL_KEY")

def league_score_for_fixture(row):
    score = 80
    league = (row.get("liga") or "").lower()
    if any(x in league for x in ("friendly","amistoso")): score = 62
    if any(x in league for x in ("u17","u18","u19","u20","u21","youth","reserve")): score = min(score,58)
    return score

st.markdown("<h1 class='joya-title'>💎 JOYA Enterprise 4.5 DEV</h1>", unsafe_allow_html=True)
st.caption("Projection Engine + Multi-Market Decision Center")

api_key = get_api_key()
if not api_key:
    st.error("Configura API_FOOTBALL_KEY en Streamlit Secrets.")
    st.stop()

with st.sidebar:
    st.header("API Manager")
    try:
        status = cached_status(api_key)
        response = status.get("response") or {}
        st.success("API-Football conectada")
        st.write("Plan:", (response.get("subscription") or {}).get("plan","—"))
        st.write("Límite diario:", (response.get("requests") or {}).get("limit_day","—"))
    except Exception as exc:
        st.warning(str(exc))
    selected_date = st.date_input("Fecha", value=date.today())
    min_score = st.slider("League Score mínimo",40,100,70)
    show_no_bet = st.checkbox("Mostrar mercados NO BET", value=False)

try:
    payload = cached_fixtures(api_key, selected_date.isoformat())
except APIFootballError as exc:
    st.error(str(exc)); st.stop()

rows = fixtures_to_rows(payload)
if not rows:
    st.info("No se encontraron partidos."); st.stop()

countries = sorted({r["país"] for r in rows if r["país"]})
country = st.selectbox("País", countries)
country_rows = [r for r in rows if r["país"] == country]
leagues = sorted({r["liga"] for r in country_rows if r["liga"]})
league = st.selectbox("Liga", leagues)
league_rows = [r for r in country_rows if r["liga"] == league]
labels = {f'{r["partido"]} · ID {r["fixture_id"]}':r for r in league_rows}
selected = labels[st.selectbox("Partido", list(labels.keys()))]
league_score = league_score_for_fixture(selected)

a,b,c = st.columns(3)
a.metric("Partidos del día",len(rows)); b.metric("League Score",league_score); c.metric("Filtro mínimo",min_score)

if league_score < min_score:
    st.error("🔴 NO BET: liga bajo el filtro."); st.stop()

if st.button("🧠 Ejecutar análisis JOYA completo",type="primary",use_container_width=True):
    with st.spinner("Ejecutando motores..."):
        try:
            pred = cached_prediction(api_key,int(selected["fixture_id"]))
            quality = evaluate_data_quality(selected["raw"],pred,league_score)
            projection = build_projection(pred,quality.score) if quality.approved else None
        except Exception as exc:
            st.error(f"Error: {exc}"); st.stop()

    st.subheader("📊 Data Quality")
    q1,q2,q3 = st.columns(3)
    q1.metric("Score",f"{quality.score:.0f}/100")
    q2.metric("Estado",quality.status)
    q3.metric("Muestra",quality.sample_quality)
    if not quality.approved:
        st.error("🔴 NO BET — motores bloqueados."); st.stop()

    st.subheader("📈 Proyección")
    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Marcador central",projection.expected_score)
    p2.metric("Goles esperados",projection.expected_goals)
    p3.metric("Marca primero",projection.first_goal_team)
    p4.metric("Confianza",f"{projection.projection_confidence:.0f}%")
    st.info(f"{projection.match_script} · Primer gol probable: {projection.first_goal_window}")

    engines = evaluate_all(projection,quality,league_score)
    ranking = global_ranking(engines)

    st.subheader("🏆 TOP 10 JOYA")
    approved = [m for m in ranking if m.status != "NO BET"][:10]
    if not approved:
        st.warning("No hay mercados aprobados.")
    for i,m in enumerate(approved,1):
        icon = "🟢" if m.status=="BET" else "🟡"
        st.markdown(f"""<div class="joya-card">
        <div class="joya-title">{i}. {icon} {m.market}</div>
        <b>{m.family}</b> · JOYA {m.joya_score}/100 · {tier(m.joya_score)} ·
        Prob. {m.probability}% · Conf. {m.confidence}% · Riesgo {m.risk}
        <div class="small-muted">{m.reason}</div></div>""",unsafe_allow_html=True)

    st.subheader("🧠 Decision Center por motor")
    for name, markets in engines.items():
        with st.expander(f"{name} Engine", expanded=name in ("Winner","Goals")):
            data = [m.to_dict() for m in markets if show_no_bet or m.status!="NO BET"]
            if not data:
                st.info("Sin mercados aprobados.")
            else:
                df = pd.DataFrame(data)
                st.dataframe(df[["market","probability","confidence","risk","joya_score","status","reason"]],
                             use_container_width=True,hide_index=True)

    with st.expander("Salida técnica completa"):
        st.json({
            "fixture":{"id":selected["fixture_id"],"home":selected["local"],"away":selected["visitante"],"league":selected["liga"]},
            "data_quality":quality.to_dict(),
            "projection":projection.to_dict(),
            "ranking":[m.to_dict() for m in ranking],
        })
