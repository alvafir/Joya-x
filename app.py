import os
from datetime import date
import pandas as pd
import streamlit as st

from modules.api import APIFootballError
from modules.cache import (
    cached_fixtures, cached_prediction, cached_status,
    cached_recent_team, cached_h2h_safe, cached_recent_statistics_batch, cached_h2h_enriched_batch
)
from modules.data_quality import evaluate_data_quality
from modules.projection import build_projection_v2
from modules.projection_v3 import build_projection_v3
from modules.intelligence_hub import build_intelligence_report
from modules.corner_intelligence import build_corner_projection
from modules.h2h_intelligence import build_h2h_report
from modules.learning_engine import save_analysis, record_result, summary_metrics, recent_analyses, initialize
from modules.scanner import fixtures_to_rows
from modules.market_orchestrator import evaluate_all, global_ranking
from modules.joya_score import tier

st.set_page_config(page_title="JOYA Enterprise 5.0", page_icon="💎", layout="wide")
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
    try: return st.secrets.get("API_FOOTBALL_KEY")
    except Exception: return os.getenv("API_FOOTBALL_KEY")

def league_score_for_fixture(row):
    score = 80
    league = (row.get("liga") or "").lower()
    if any(x in league for x in ("friendly","amistoso")): score = 62
    if any(x in league for x in ("u17","u18","u19","u20","u21","youth","reserve")):
        score = min(score,58)
    return score

st.markdown("<h1 class='joya-title'>💎 JOYA Enterprise 5.4 · API Markets + Cartillas DEV</h1>", unsafe_allow_html=True)
st.caption("API Market Discovery · Proyección JOYA · Cartillas Globales")

api_key = get_api_key()
if not api_key:
    st.error("Configura API_FOOTBALL_KEY en Streamlit Secrets."); st.stop()

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
    show_no_bet = st.checkbox("Mostrar NO BET",False)

try:
    payload = cached_fixtures(api_key, selected_date.isoformat())
except APIFootballError as exc:
    st.error(str(exc)); st.stop()

rows = fixtures_to_rows(payload)
if not rows:
    st.info("No se encontraron partidos."); st.stop()

countries = sorted({r["país"] for r in rows if r["país"]})
country = st.selectbox("País",countries)
country_rows=[r for r in rows if r["país"]==country]
leagues=sorted({r["liga"] for r in country_rows if r["liga"]})
league=st.selectbox("Liga",leagues)
league_rows=[r for r in country_rows if r["liga"]==league]
labels={f'{r["partido"]} · ID {r["fixture_id"]}':r for r in league_rows}
selected=labels[st.selectbox("Partido",list(labels.keys()))]
league_score=league_score_for_fixture(selected)

a,b,c=st.columns(3)
a.metric("Partidos del día",len(rows)); b.metric("League Score",league_score); c.metric("Filtro mínimo",min_score)

if league_score < min_score:
    st.error("🔴 NO BET: liga bajo filtro."); st.stop()

if st.button("🧠 Ejecutar análisis JOYA 5.2",type="primary",use_container_width=True):
    raw = selected["raw"]
    teams = raw.get("teams") or {}
    home_id = ((teams.get("home") or {}).get("id"))
    away_id = ((teams.get("away") or {}).get("id"))
    if not home_id or not away_id:
        st.error("No se encontraron IDs de equipos."); st.stop()

    with st.spinner("Consultando forma, local/visita, H2H y predicción..."):
        try:
            pred = cached_prediction(api_key,int(selected["fixture_id"]))
            home_recent = cached_recent_team(api_key,int(home_id),20)
            away_recent = cached_recent_team(api_key,int(away_id),20)
            h2h_result = cached_h2h_safe(api_key,int(home_id),int(away_id),10)
            h2h = h2h_result["payload"]
            quality = evaluate_data_quality(raw,pred,league_score)
            projection = build_projection_v2(
                pred,home_recent,away_recent,h2h,
                int(home_id),int(away_id),quality.score
            )
            intelligence = build_intelligence_report(
                home_recent, away_recent,
                int(home_id), int(away_id), league_score
            )
            projection_v3 = build_projection_v3(projection, intelligence)
            projection = projection_v3.base

            home_corner_batch = cached_recent_statistics_batch(
                api_key, home_recent, limit=8
            )
            away_corner_batch = cached_recent_statistics_batch(
                api_key, away_recent, limit=8
            )
            corner_projection = build_corner_projection(
                home_corner_batch,
                away_corner_batch,
                int(home_id),
                int(away_id),
                league_score,
            )

            h2h_enriched = cached_h2h_enriched_batch(
                api_key,
                h2h,
                limit=10,
            )
            h2h_report = build_h2h_report(
                h2h_enriched,
                int(home_id),
                int(away_id),
            )
        except Exception as exc:
            st.error(f"Error al ejecutar JOYA: {exc}"); st.stop()

    source_status = {
        "Predicción API": "OK",
        "Forma local": "OK" if (home_recent.get("response") or []) else "SIN DATOS",
        "Forma visitante": "OK" if (away_recent.get("response") or []) else "SIN DATOS",
        "H2H": "OK" if h2h_result["ok"] else "OPCIONAL NO DISPONIBLE",
    }

    if h2h_result.get("warning"):
        projection.warnings.append(h2h_result["warning"])

    st.subheader("📡 Estado de fuentes")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Predicción", source_status["Predicción API"])
    f2.metric("Forma local", source_status["Forma local"])
    f3.metric("Forma visitante", source_status["Forma visitante"])
    f4.metric("H2H", source_status["H2H"])

    st.subheader("📊 Data Quality")
    q1,q2,q3=st.columns(3)
    q1.metric("Score",f"{quality.score:.0f}/100")
    q2.metric("Estado",quality.status)
    q3.metric("Muestra",quality.sample_quality)

    st.subheader("📈 Projection Engine 2.0")
    p1,p2,p3,p4=st.columns(4)
    p1.metric("Marcador central",projection.expected_score)
    p2.metric("Goles esperados",projection.expected_goals)
    p3.metric("Marca primero",projection.first_goal_team)
    p4.metric("Confianza",f"{projection.projection_confidence:.0f}%")

    s1,s2,s3,s4=st.columns(4)
    s1.metric("Muestra local",projection.sample_home)
    s2.metric("Muestra visitante",projection.sample_away)
    s3.metric("H2H",projection.sample_h2h)
    s4.metric("Calidad fuentes",f"{projection.source_quality:.0f}/100")

    st.info(f"{projection.match_script} · Fuente: {projection.projection_source} · Primer gol: {projection.first_goal_window}")

    st.subheader("🧠 Intelligence Hub")
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Cobertura", f"{intelligence.coverage:.0f}/100")
    i2.metric("Volatilidad", f"{intelligence.volatility:.0f}/100")
    i3.metric("Estabilidad", f"{projection_v3.stability:.0f}/100")
    i4.metric("Incertidumbre", f"{projection_v3.uncertainty:.0f}/100")

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Escenario conservador", projection_v3.conservative.score)
    sc2.metric("Escenario central", projection_v3.central.score)
    sc3.metric("Escenario ofensivo", projection_v3.offensive.score)
    st.caption(projection_v3.narrative)

    for warning in projection_v3.warnings:
        st.warning(warning)

    st.subheader("🤝 H2H Intelligence")
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("H2H Score", f"{h2h_report.score:.0f}/100")
    h2.metric("Muestra", h2h_report.sample)
    h3.metric("Peso", h2h_report.weight_label)
    h4.metric("Confianza", f"{h2h_report.confidence:.0f}%")

    hm1, hm2, hm3, hm4 = st.columns(4)
    hm1.metric("Promedio goles", h2h_report.avg_goals)
    hm2.metric("BTTS", f"{h2h_report.btts_rate:.0f}%")
    hm3.metric("Over 2.5", f"{h2h_report.over_25_rate:.0f}%")
    hm4.metric(
        "Córners H2H",
        h2h_report.avg_corners if h2h_report.avg_corners is not None else "Sin datos",
    )

    for reason in h2h_report.reasons:
        st.caption(f"• {reason}")
    for warning in h2h_report.warnings[:3]:
        st.warning(warning)

    st.subheader("🚩 Corner Intelligence")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Córners esperados", corner_projection.total_expected)
    c2.metric("Local esperado", corner_projection.home_expected)
    c3.metric("Visitante esperado", corner_projection.away_expected)
    c4.metric("Confianza", f"{corner_projection.confidence:.0f}%")

    cs1, cs2, cs3 = st.columns(3)
    cs1.metric("Muestra local", corner_projection.home.sample)
    cs2.metric("Muestra visitante", corner_projection.away.sample)
    cs3.metric("Calidad muestra", f"{corner_projection.sample_quality:.0f}/100")

    for warning in corner_projection.warnings[:4]:
        st.warning(warning)

    engines=evaluate_all(
        projection,
        quality,
        league_score,
        corner_projection=corner_projection,
        h2h_report=h2h_report,
    )
    ranking=global_ranking(engines,20)

    fixture_record = {
        "id": int(selected["fixture_id"]),
        "home": selected["local"],
        "away": selected["visitante"],
        "league": selected["liga"],
    }
    save_analysis(
        fixture_record,
        projection_v3.to_dict(),
        [m.to_dict() for m in ranking],
    )

    st.subheader("🏆 TOP 10 JOYA DIVERSIFICADO")
    approved=[m for m in ranking if m.status!="NO BET"][:10]
    if not approved:
        st.warning("No hay mercados aprobados.")
    for i,m in enumerate(approved,1):
        icon="🟢" if m.status=="BET" else "🟡"
        st.markdown(f"""<div class="joya-card">
        <div class="joya-title">{i}. {icon} {m.market}</div>
        <b>{m.family}</b> · JOYA {m.joya_score}/100 · {tier(m.joya_score)} ·
        Prob. {m.probability}% · Conf. {m.confidence}% · Riesgo {m.risk}
        <div class="small-muted">{m.reason}</div></div>""",unsafe_allow_html=True)

    st.subheader("🧠 Decision Center")
    for name,markets in engines.items():
        with st.expander(f"{name} Engine",expanded=name in ("Winner","Goals")):
            data=[m.to_dict() for m in markets if show_no_bet or m.status!="NO BET"]
            if not data:
                st.info("Sin mercados aprobados.")
            else:
                df=pd.DataFrame(data)
                st.dataframe(df[["market","probability","confidence","risk","joya_score","status","reason"]],
                             use_container_width=True,hide_index=True)

    st.subheader("🏪 Market Center")

    all_market_rows = [
        m.to_dict()
        for family_markets in engines.values()
        for m in family_markets
    ]
    market_df = pd.DataFrame(all_market_rows)

    if not market_df.empty:
        mc1, mc2, mc3, mc4 = st.columns(4)
        family_options = ["Todas"] + sorted(market_df["family"].dropna().unique().tolist())
        status_options = ["Todos"] + sorted(market_df["status"].dropna().unique().tolist())
        risk_options = ["Todos"] + sorted(market_df["risk"].dropna().unique().tolist())

        selected_family = mc1.selectbox("Familia", family_options, key="market_family")
        selected_status = mc2.selectbox("Estado", status_options, key="market_status")
        selected_risk = mc3.selectbox("Riesgo", risk_options, key="market_risk")
        min_joya = mc4.slider("JOYA Score mínimo", 0, 100, 70, key="market_min_joya")

        filtered = market_df.copy()
        if selected_family != "Todas":
            filtered = filtered[filtered["family"] == selected_family]
        if selected_status != "Todos":
            filtered = filtered[filtered["status"] == selected_status]
        if selected_risk != "Todos":
            filtered = filtered[filtered["risk"] == selected_risk]

        filtered = filtered[filtered["joya_score"] >= min_joya]
        filtered = filtered.sort_values("joya_score", ascending=False)

        rec_tab, caution_tab, rejected_tab = st.tabs(
            ["🟢 Recomendados", "🟡 Precaución", "🔴 Descartados"]
        )

        with rec_tab:
            recommended = filtered[filtered["status"] == "BET"]
            if recommended.empty:
                st.info("Sin mercados BET para estos filtros.")
            else:
                st.dataframe(
                    recommended[
                        ["family", "market", "probability", "confidence",
                         "risk", "joya_score", "reason"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        with caution_tab:
            caution = filtered[filtered["status"] == "PRECAUCIÓN"]
            if caution.empty:
                st.info("Sin mercados PRECAUCIÓN para estos filtros.")
            else:
                st.dataframe(
                    caution[
                        ["family", "market", "probability", "confidence",
                         "risk", "joya_score", "reason"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        with rejected_tab:
            rejected = market_df[market_df["status"] == "NO BET"].sort_values(
                "joya_score", ascending=False
            )
            if rejected.empty:
                st.info("Sin mercados descartados.")
            else:
                st.dataframe(
                    rejected[
                        ["family", "market", "probability", "confidence",
                         "risk", "joya_score", "reason"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

    with st.expander("Trazabilidad completa"):
        st.json({
            "fixture":{"id":selected["fixture_id"],"home":selected["local"],"away":selected["visitante"]},
            "quality":quality.to_dict(),
            "intelligence":intelligence.to_dict(),
            "projection_v3":projection_v3.to_dict(),
            "corner_projection":corner_projection.to_dict(),
            "h2h_report":h2h_report.to_dict(),
            "ranking":[m.to_dict() for m in ranking],
        })


st.divider()
st.subheader("📚 Learning Engine")

initialize()
metrics = summary_metrics()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Mercados evaluados", metrics["settled"])
m2.metric("Aciertos", metrics["wins"])
m3.metric("Precisión histórica", f'{metrics["accuracy"]:.1f}%')
m4.metric("Error medio de goles", metrics["goal_mae"])

with st.expander("Registrar resultado final"):
    fixture_result_id = st.number_input("Fixture ID", min_value=1, step=1)
    rg1, rg2 = st.columns(2)
    final_home = rg1.number_input("Goles local", min_value=0, max_value=20, step=1)
    final_away = rg2.number_input("Goles visitante", min_value=0, max_value=20, step=1)
    result_notes = st.text_input("Notas opcionales")
    if st.button("Guardar resultado y liquidar mercados"):
        record_result(
            int(fixture_result_id),
            int(final_home),
            int(final_away),
            result_notes,
        )
        st.success("Resultado guardado. Las métricas se actualizarán al recargar.")

with st.expander("Historial reciente"):
    history = recent_analyses(30)
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("Aún no existen análisis guardados.")

if metrics["by_family"]:
    with st.expander("Precisión por familia"):
        family_df = pd.DataFrame(metrics["by_family"])
        family_df["accuracy"] = (
            family_df["wins"] / family_df["settled"] * 100
        ).round(1)
        st.dataframe(family_df, use_container_width=True, hide_index=True)
