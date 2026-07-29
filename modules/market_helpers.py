from .models import MarketDecision
from .joya_score import calculate_joya_score, classify_status
from .utils import clamp

def risk_from_probability(probability: float) -> str:
    if probability >= 86:
        return "Bajo"
    if probability >= 72:
        return "Medio"
    return "Alto"

def make_decision(
    family: str,
    market: str,
    probability: float,
    projection_confidence: float,
    data_quality: float,
    league_score: float,
    reason: str,
    sample_penalty: float = 0.0,
) -> MarketDecision:
    probability = clamp(probability)
    risk = risk_from_probability(probability)
    confidence = clamp(
        projection_confidence * 0.58
        + data_quality * 0.24
        + probability * 0.18
        - sample_penalty
    )
    score = calculate_joya_score(
        probability=probability,
        confidence=confidence,
        data_quality=data_quality,
        league_score=league_score,
        risk=risk,
        projection_confidence=projection_confidence,
        sample_penalty=sample_penalty,
    )
    status = classify_status(score, data_quality, probability)
    return MarketDecision(
        family=family,
        market=market,
        probability=round(probability, 1),
        confidence=round(confidence, 1),
        risk=risk,
        league_score=round(league_score, 1),
        data_quality=round(data_quality, 1),
        joya_score=score,
        status=status,
        reason=reason,
    )

def no_bet(family: str, market: str, league_score: float, data_quality: float, reason: str):
    return MarketDecision(
        family=family,
        market=market,
        probability=0.0,
        confidence=0.0,
        risk="Alto",
        league_score=round(league_score, 1),
        data_quality=round(data_quality, 1),
        joya_score=0.0,
        status="NO BET",
        reason=reason,
    )
