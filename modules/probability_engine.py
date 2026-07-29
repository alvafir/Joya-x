from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ProbabilityResult:
    home: int | None
    draw: int | None
    away: int | None
    confidence: int
    risk: str
    status: str
    recommendation: str
    explanation: str
    source_quality: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_three_way(
    home: int | None,
    draw: int | None,
    away: int | None,
) -> tuple[int | None, int | None, int | None]:
    values = [home, draw, away]

    if any(value is None for value in values):
        return home, draw, away

    total = sum(values)

    if total <= 0:
        return home, draw, away

    normalized = [round((value / total) * 100) for value in values]
    difference = 100 - sum(normalized)

    if difference:
        max_index = normalized.index(max(normalized))
        normalized[max_index] += difference

    return normalized[0], normalized[1], normalized[2]


def _source_quality(parsed_prediction: dict) -> int:
    score = 40

    if parsed_prediction.get("data_complete"):
        score += 25

    if parsed_prediction.get("winner_name") not in {"", "Sin favorito"}:
        score += 10

    comparison = parsed_prediction.get("comparison") or {}

    if isinstance(comparison, dict) and comparison:
        score += 15

    if parsed_prediction.get("advice") not in {"", "Sin recomendación"}:
        score += 10

    return max(0, min(100, score))


def _confidence_from_margin(
    home: int | None,
    draw: int | None,
    away: int | None,
    quality: int,
) -> int:
    available = [value for value in [home, draw, away] if value is not None]

    if len(available) != 3:
        return min(55, quality)

    ordered = sorted(available, reverse=True)
    margin = ordered[0] - ordered[1]

    confidence = 45 + int(margin * 1.4) + int((quality - 50) * 0.35)

    return max(0, min(95, confidence))


def _risk_level(confidence: int, quality: int) -> str:
    if confidence >= 80 and quality >= 80:
        return "Bajo"
    if confidence >= 65 and quality >= 65:
        return "Medio"
    return "Alto"


def _status(confidence: int, quality: int) -> str:
    if confidence >= 82 and quality >= 80:
        return "🟢 BET"
    if confidence >= 68 and quality >= 65:
        return "🟡 PRECAUCIÓN"
    return "🔴 NO BET"


def calculate_joya_probability(parsed_prediction: dict) -> ProbabilityResult:
    """
    Calcula una salida JOYA conservadora usando solo datos disponibles
    en la predicción oficial de API-Football.

    No inventa forma, xG, lesiones, H2H ni muestras históricas.
    """
    home, draw, away = _normalize_three_way(
        parsed_prediction.get("home_percent"),
        parsed_prediction.get("draw_percent"),
        parsed_prediction.get("away_percent"),
    )

    quality = _source_quality(parsed_prediction)
    confidence = _confidence_from_margin(home, draw, away, quality)
    risk = _risk_level(confidence, quality)
    status = _status(confidence, quality)

    winner = parsed_prediction.get("winner_name") or "Sin favorito"
    advice = parsed_prediction.get("advice") or "Sin recomendación"

    if status == "🟢 BET":
        recommendation = winner
    elif status == "🟡 PRECAUCIÓN":
        recommendation = f"Revisar {winner}"
    else:
        recommendation = "NO BET"

    explanation = (
        f"Base: probabilidades disponibles en API-Football. "
        f"Calidad de fuente: {quality}/100. "
        f"Consejo API: {advice}. "
        "Este resultado todavía no incorpora forma propia, xG, lesiones "
        "ni calibración histórica JOYA."
    )

    return ProbabilityResult(
        home=home,
        draw=draw,
        away=away,
        confidence=confidence,
        risk=risk,
        status=status,
        recommendation=recommendation,
        explanation=explanation,
        source_quality=quality,
    )
