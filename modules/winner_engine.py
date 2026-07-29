from typing import List
from .models import DataQualityResult, MarketDecision, ProjectionResult
from .joya_score import calculate_joya_score, classify_status
from .utils import clamp

def _risk(probability: float, draw_probability: float) -> str:
    if probability >= 88 and draw_probability <= 30:
        return "Bajo"
    if probability >= 76:
        return "Medio"
    return "Alto"

def _decision(
    market: str,
    probability: float,
    projection: ProjectionResult,
    quality: DataQualityResult,
    league_score: float,
    reason: str,
) -> MarketDecision:
    risk = _risk(probability, projection.draw)
    confidence = clamp(
        projection.projection_confidence * 0.65
        + quality.score * 0.20
        + probability * 0.15
    )
    score = calculate_joya_score(
        probability, confidence, quality.score, league_score, risk
    )
    status = classify_status(score, quality.score)
    return MarketDecision(
        family="Winner",
        market=market,
        probability=round(probability, 1),
        confidence=round(confidence, 1),
        risk=risk,
        league_score=round(league_score, 1),
        data_quality=quality.score,
        joya_score=score,
        status=status,
        reason=reason,
    )

def evaluate_winner_markets(
    projection: ProjectionResult,
    quality: DataQualityResult,
    league_score: float = 80.0,
) -> List[MarketDecision]:
    if not quality.approved:
        return [
            MarketDecision(
                family="Winner",
                market="Mercados de ganador",
                probability=0.0,
                confidence=0.0,
                risk="Alto",
                league_score=round(league_score, 1),
                data_quality=quality.score,
                joya_score=0.0,
                status="NO BET",
                reason="Data Quality no aprobada; motor bloqueado.",
            )
        ]

    h, d, a = projection.home_win, projection.draw, projection.away_win
    results = [
        _decision("Local 1", h, projection, quality, league_score,
                  "Probabilidad directa de victoria local."),
        _decision("Empate X", d, projection, quality, league_score,
                  "Probabilidad directa de empate."),
        _decision("Visitante 2", a, projection, quality, league_score,
                  "Probabilidad directa de victoria visitante."),
        _decision("Doble oportunidad 1X", h + d, projection, quality, league_score,
                  "Cubre victoria local y empate."),
        _decision("Doble oportunidad X2", a + d, projection, quality, league_score,
                  "Cubre victoria visitante y empate."),
        _decision("Doble oportunidad 12", h + a, projection, quality, league_score,
                  "Cubre cualquier ganador y excluye el empate."),
    ]

    # DNB condicional, eliminando el empate y normalizando.
    non_draw = h + a
    if non_draw > 0:
        home_dnb = h / non_draw * 100
        away_dnb = a / non_draw * 100
        results.extend([
            _decision("Local DNB", home_dnb, projection, quality, league_score,
                      "Probabilidad condicional al excluir el empate."),
            _decision("Visitante DNB", away_dnb, projection, quality, league_score,
                      "Probabilidad condicional al excluir el empate."),
        ])

    return sorted(results, key=lambda x: x.joya_score, reverse=True)
