from .utils import clamp

RISK_PENALTY = {"Bajo": 0.0, "Medio": 6.0, "Alto": 14.0}

def calculate_joya_score(
    probability: float,
    confidence: float,
    data_quality: float,
    league_score: float,
    risk: str,
) -> float:
    score = (
        probability * 0.42
        + confidence * 0.28
        + data_quality * 0.18
        + league_score * 0.12
        - RISK_PENALTY.get(risk, 10.0)
    )
    return round(clamp(score), 1)

def classify_status(score: float, data_quality: float) -> str:
    if data_quality < 70 or score < 70:
        return "NO BET"
    if score >= 90:
        return "BET"
    if score >= 80:
        return "PRECAUCIÓN"
    return "NO BET"
