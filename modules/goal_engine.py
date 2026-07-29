import math
from typing import List, Optional
from .models import DataQualityResult, MarketDecision, ProjectionResult
from .market_helpers import make_decision, no_bet
from .utils import clamp
from .h2h_blend import blend_probability, h2h_reason
from .h2h_intelligence import H2HReport

def poisson_cdf(k: int, lam: float) -> float:
    return sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))

def over_probability(line: float, lam: float) -> float:
    threshold = int(math.floor(line))
    return clamp((1.0 - poisson_cdf(threshold, lam)) * 100.0)

def under_probability(line: float, lam: float) -> float:
    threshold = int(math.floor(line))
    return clamp(poisson_cdf(threshold, lam) * 100.0)

def team_over_05(lam: float) -> float:
    return clamp((1.0 - math.exp(-lam)) * 100.0)

def team_over_15(lam: float) -> float:
    return over_probability(1.5, lam)

def btts_yes(home_lam: float, away_lam: float) -> float:
    return clamp((1-math.exp(-home_lam))*(1-math.exp(-away_lam))*100.0)

def first_half_lambda(total_lam: float) -> float:
    return max(0.0, total_lam * 0.44)

def evaluate_goal_markets(
    projection: ProjectionResult,
    quality: DataQualityResult,
    league_score: float = 80.0,
    h2h_report: Optional[H2HReport] = None,
) -> List[MarketDecision]:
    if not quality.approved:
        return [no_bet("Goals", "Mercados de goles", league_score, quality.score,
                       "Data Quality no aprobada.")]

    total = projection.expected_goals
    home = projection.home_expected_goals
    away = projection.away_expected_goals
    pc = projection.projection_confidence
    dq = quality.score
    out: List[MarketDecision] = []

    # Totales FT
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        over_prob = over_probability(line, total)
        if h2h_report and h2h_report.available:
            if line == 1.5:
                over_prob = blend_probability(over_prob, h2h_report.over_15_rate, h2h_report, 0.14)
            elif line == 2.5:
                over_prob = blend_probability(over_prob, h2h_report.over_25_rate, h2h_report, 0.14)
        out.append(make_decision("Goals", f"Más de {line} goles FT",
                                 over_prob, pc, dq, league_score,
                                 f"Modelo Poisson sobre {total:.2f} goles esperados."))
        out.append(make_decision("Goals", f"Menos de {line} goles FT",
                                 under_probability(line, total), pc, dq, league_score,
                                 f"Modelo Poisson sobre {total:.2f} goles esperados."))

    # Primer tiempo, con penalización por aproximación
    first_lam = first_half_lambda(total)
    for line in (0.5, 1.5, 2.5):
        out.append(make_decision("Goals 1T", f"Más de {line} goles 1T",
                                 over_probability(line, first_lam), pc, dq, league_score,
                                 "Proyección 1T derivada del ritmo total; requiere cautela.",
                                 sample_penalty=5.0))
        out.append(make_decision("Goals 1T", f"Menos de {line} goles 1T",
                                 under_probability(line, first_lam), pc, dq, league_score,
                                 "Proyección 1T derivada del ritmo total; requiere cautela.",
                                 sample_penalty=5.0))

    # BTTS
    yes = btts_yes(home, away)
    if h2h_report and h2h_report.available:
        yes = blend_probability(yes, h2h_report.btts_rate, h2h_report, 0.14)
    out.append(make_decision("Goals", "Ambos marcan — Sí", yes, pc, dq, league_score,
                             "Probabilidad conjunta de que ambos equipos anoten." + h2h_reason(h2h_report, "BTTS", h2h_report.btts_rate if h2h_report else 0)))
    out.append(make_decision("Goals", "Ambos marcan — No", 100-yes, pc, dq, league_score,
                             "Complemento de la probabilidad BTTS Sí."))

    # Equipo
    for label, lam in (("Local", home), ("Visitante", away)):
        out.append(make_decision("Team Goals", f"{label} más de 0.5 goles",
                                 team_over_05(lam), pc, dq, league_score,
                                 f"Proyección individual: {lam:.2f} goles."))
        out.append(make_decision("Team Goals", f"{label} más de 1.5 goles",
                                 team_over_15(lam), pc, dq, league_score,
                                 f"Proyección individual: {lam:.2f} goles."))
        out.append(make_decision("Team Goals", f"{label} portería a cero",
                                 100-team_over_05(away if label == "Local" else home),
                                 pc, dq, league_score,
                                 "Probabilidad de que el rival no anote."))

    # Tiempo
    time_markets = [
        ("Ningún gol antes del minuto 10", projection.no_goal_before_10),
        ("Ningún gol antes del minuto 20", projection.no_goal_before_20),
        ("Gol antes del minuto 60", 100 - math.exp(-total * 60/90) * 100),
        ("Gol antes del minuto 70", projection.goal_before_70),
        ("Gol antes del minuto 80", projection.goal_before_80),
    ]
    for market, prob in time_markets:
        out.append(make_decision("Goal Timing", market, prob, pc, dq, league_score,
                                 "Proyección temporal basada en tasa esperada de gol.",
                                 sample_penalty=3.0))

    # Marca primero
    total_team = home + away
    if total_team > 0:
        home_first = clamp(home / total_team * projection.goal_before_80)
        away_first = clamp(away / total_team * projection.goal_before_80)
        no_goal = clamp(100 - projection.goal_before_80)
        out.append(make_decision("First Goal", "Local marca primero", home_first, pc, dq, league_score,
                                 "Distribución del primer gol según fuerza goleadora proyectada.",
                                 sample_penalty=4.0))
        out.append(make_decision("First Goal", "Visitante marca primero", away_first, pc, dq, league_score,
                                 "Distribución del primer gol según fuerza goleadora proyectada.",
                                 sample_penalty=4.0))
        out.append(make_decision("First Goal", "Sin gol", no_goal, pc, dq, league_score,
                                 "Probabilidad residual de partido sin gol.",
                                 sample_penalty=4.0))

    # Rango de goles
    ranges = {
        "Rango 1-5 goles": 100 - math.exp(-total) - (1 - poisson_cdf(5, total)),
        "Rango 1-4 goles": 100 - math.exp(-total) - (1 - poisson_cdf(4, total)),
        "Rango 2-5 goles": poisson_cdf(5, total) - poisson_cdf(1, total),
        "Rango 2-4 goles": poisson_cdf(4, total) - poisson_cdf(1, total),
    }
    for market, raw in ranges.items():
        prob = raw * 100 if raw <= 1 else raw
        out.append(make_decision("Goal Range", market, prob, pc, dq, league_score,
                                 "Rango calculado con distribución Poisson."))

    return sorted(out, key=lambda x: x.joya_score, reverse=True)
