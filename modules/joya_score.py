from .utils import clamp

RISK_PENALTY = {"Bajo": 0.0, "Medio": 5.0, "Alto": 14.0}

def calculate_joya_score(
    probability: float,
    confidence: float,
    data_quality: float,
    league_score: float,
    risk: str,
    projection_confidence: float = 0.0,
    sample_penalty: float = 0.0,
    stability: float = 75.0,
    historical_accuracy: float = 75.0,
    correlation_penalty: float = 0.0,
) -> float:
    score = (
        probability * 0.31
        + confidence * 0.18
        + data_quality * 0.13
        + league_score * 0.08
        + projection_confidence * 0.10
        + stability * 0.11
        + historical_accuracy * 0.09
        - RISK_PENALTY.get(risk, 10.0)
        - sample_penalty
        - correlation_penalty
    )
    return round(clamp(score), 1)

def classify_status(score: float, data_quality: float, probability: float) -> str:
    if data_quality < 70 or probability < 60 or score < 70:
        return "NO BET"
    if score >= 90 and probability >= 78:
        return "BET"
    if score >= 80 and probability >= 68:
        return "PRECAUCIÓN"
    return "NO BET"

def tier(score: float) -> str:
    if score >= 95: return "ELITE"
    if score >= 92: return "S+++"
    if score >= 88: return "S++"
    if score >= 84: return "S+"
    if score >= 80: return "A++"
    return "NO BET"
