from typing import List
from .models import DataQualityResult, MarketDecision, ProjectionResult
from .market_helpers import make_decision, no_bet
from .utils import clamp

def evaluate_winner_markets(
    projection: ProjectionResult,
    quality: DataQualityResult,
    league_score: float = 80.0,
) -> List[MarketDecision]:
    if not quality.approved:
        return [no_bet("Winner", "Mercados de ganador", league_score, quality.score,
                       "Data Quality no aprobada; motor bloqueado.")]

    h, d, a = projection.home_win, projection.draw, projection.away_win
    pc, dq = projection.projection_confidence, quality.score
    out = []

    base = [
        ("Local 1", h, "Probabilidad directa de victoria local.", 0),
        ("Empate X", d, "Probabilidad directa de empate.", 0),
        ("Visitante 2", a, "Probabilidad directa de victoria visitante.", 0),
        ("Doble oportunidad 1X", h+d, "Cubre local o empate.", 0),
        ("Doble oportunidad X2", a+d, "Cubre visitante o empate.", 0),
        ("Doble oportunidad 12", h+a, "Cubre cualquier ganador.", 0),
    ]
    for market, prob, reason, penalty in base:
        out.append(make_decision("Winner", market, prob, pc, dq, league_score, reason, penalty))

    non_draw = h+a
    if non_draw > 0:
        out.append(make_decision("Winner", "Local DNB", h/non_draw*100, pc, dq, league_score,
                                 "Probabilidad condicional sin empate."))
        out.append(make_decision("Winner", "Visitante DNB", a/non_draw*100, pc, dq, league_score,
                                 "Probabilidad condicional sin empate."))

    # Aproximaciones por tiempos
    home_any_half = clamp(55 + (h-33)*0.72)
    away_any_half = clamp(55 + (a-33)*0.72)
    home_1h = clamp(20 + h*0.58)
    draw_1h = clamp(60 - abs(h-a)*0.35)
    away_1h = clamp(20 + a*0.58)
    s = home_1h + draw_1h + away_1h
    home_1h, draw_1h, away_1h = [x*100/s for x in (home_1h, draw_1h, away_1h)]

    time_markets = [
        ("Local gana cualquier mitad", home_any_half),
        ("Visitante gana cualquier mitad", away_any_half),
        ("Local gana 1T", home_1h),
        ("Empate 1T", draw_1h),
        ("Visitante gana 1T", away_1h),
        ("Doble oportunidad 1X 1T", home_1h+draw_1h),
        ("Doble oportunidad X2 1T", away_1h+draw_1h),
        ("Doble oportunidad 12 1T", home_1h+away_1h),
    ]
    for market, prob in time_markets:
        out.append(make_decision("Winner 1T", market, prob, pc, dq, league_score,
                                 "Estimación por tiempo derivada del 1X2 FT; penalizada por menor muestra.",
                                 sample_penalty=7.0))

    return sorted(out, key=lambda x: x.joya_score, reverse=True)
