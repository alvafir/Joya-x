import math
from typing import List

from .corner_intelligence import CornerProjection
from .market_helpers import make_decision, no_bet
from .models import DataQualityResult, MarketDecision, ProjectionResult
from .utils import clamp


def _poisson_cdf(k: int, lam: float) -> float:
    return sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))


def _over(line: float, lam: float) -> float:
    return clamp((1 - _poisson_cdf(int(math.floor(line)), lam)) * 100)


def _under(line: float, lam: float) -> float:
    return clamp(_poisson_cdf(int(math.floor(line)), lam) * 100)


def _range_probability(low: int, high: int, lam: float) -> float:
    lower = _poisson_cdf(low - 1, lam) if low > 0 else 0
    upper = _poisson_cdf(high, lam)
    return clamp((upper - lower) * 100)


def evaluate(
    projection: ProjectionResult,
    quality: DataQualityResult,
    league_score: float = 80.0,
    corner_projection: CornerProjection = None,
) -> List[MarketDecision]:
    if corner_projection is None or not corner_projection.approved:
        reason = "Sin estadísticas específicas suficientes de córners."
        if corner_projection and corner_projection.warnings:
            reason = " ".join(corner_projection.warnings)
        return [
            no_bet("Corners", "Mercados de córners", league_score, quality.score, reason)
        ]

    cp = corner_projection
    pc = cp.confidence
    dq = min(quality.score, cp.sample_quality)
    out: List[MarketDecision] = []

    for line in (7.5, 8.5, 9.5, 10.5, 11.5):
        out.append(make_decision(
            "Corners",
            f"Más de {line} córners",
            _over(line, cp.total_expected),
            pc,
            dq,
            league_score,
            f"Proyección central de {cp.total_expected:.2f} córners; muestra {cp.home.sample}+{cp.away.sample}.",
            sample_penalty=2.0 if min(cp.home.sample, cp.away.sample) < 6 else 0.0,
        ))
        out.append(make_decision(
            "Corners",
            f"Menos de {line} córners",
            _under(line, cp.total_expected),
            pc,
            dq,
            league_score,
            f"Proyección central de {cp.total_expected:.2f} córners.",
            sample_penalty=2.0 if min(cp.home.sample, cp.away.sample) < 6 else 0.0,
        ))

    for label, lam, lines in (
        ("Local", cp.home_expected, (3.5, 4.5, 5.5)),
        ("Visitante", cp.away_expected, (2.5, 3.5, 4.5)),
    ):
        for line in lines:
            out.append(make_decision(
                "Team Corners",
                f"{label} más de {line} córners",
                _over(line, lam),
                pc,
                dq,
                league_score,
                f"Proyección individual de {lam:.2f} córners para {label.lower()}.",
                sample_penalty=3.0,
            ))

    total_strength = cp.home_expected + cp.away_expected
    if total_strength > 0:
        home_more = clamp(50 + (cp.home_expected - cp.away_expected) * 9)
        away_more = clamp(100 - home_more)
        out.append(make_decision(
            "Corner Winner",
            "Local tendrá más córners",
            home_more,
            pc,
            dq,
            league_score,
            "Comparación entre las proyecciones individuales de córners.",
            sample_penalty=4.0,
        ))
        out.append(make_decision(
            "Corner Winner",
            "Visitante tendrá más córners",
            away_more,
            pc,
            dq,
            league_score,
            "Comparación entre las proyecciones individuales de córners.",
            sample_penalty=4.0,
        ))

    out.append(make_decision(
        "Corner Range",
        "Rango 7-13 córners",
        _range_probability(7, 13, cp.total_expected),
        pc,
        dq,
        league_score,
        "Rango calculado mediante distribución Poisson.",
        sample_penalty=2.0,
    ))
    out.append(make_decision(
        "Corner Range",
        "Rango 8-12 córners",
        _range_probability(8, 12, cp.total_expected),
        pc,
        dq,
        league_score,
        "Rango calculado mediante distribución Poisson.",
        sample_penalty=2.0,
    ))

    return sorted(out, key=lambda item: item.joya_score, reverse=True)
