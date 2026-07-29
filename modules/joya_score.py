from .utils import clamp

RISK_PENALTY = {"Bajo": 0.0, "Medio": 5.0, "Alto": 13.0}

def calculate_joya_score(
    probability: float,
    confidence: float,
    data_quality: float,
    league_score: float,
    risk: str,
    projection_confidence: float = 0.0,
    sample_penalty: float = 0.0,
) -> float:
    score = (
        probability * 0.38
        + confidence * 0.22
        + data_quality * 0.16
        + league_score * 0.10
        + projection_confidence * 0.14
        - RISK_PENALTY.get(risk, 10.0)
        - sample_penalty
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
    if score >= 95:
        return "ELITE"
    if score >= 90:
        return "S+++"
    if score >= 86:
        return "S++"
    if score >= 82:
        return "S+"
    if score >= 78:
        return "A++"
    return "NO BET"
