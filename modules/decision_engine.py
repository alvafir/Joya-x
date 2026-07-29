from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class MarketDecision:
    family: str
    market: str
    probability: int | None
    confidence: int
    risk: str
    sample_quality: int
    league_score: int | None
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _risk(confidence: int, quality: int) -> str:
    if confidence >= 82 and quality >= 80:
        return "Bajo"
    if confidence >= 68 and quality >= 65:
        return "Medio"
    return "Alto"


def _status(confidence: int, quality: int) -> str:
    if confidence >= 84 and quality >= 80:
        return "🟢 BET"
    if confidence >= 70 and quality >= 65:
        return "🟡 PRECAUCIÓN"
    return "🔴 NO BET"


def build_market(
    family: str,
    market: str,
    probability: int | None,
    confidence: int,
    sample_quality: int,
    league_score: int | None,
    reason: str,
) -> MarketDecision:
    if probability is None:
        confidence = min(confidence, 45)
        sample_quality = min(sample_quality, 45)

    return MarketDecision(
        family=family,
        market=market,
        probability=probability,
        confidence=max(0, min(95, int(confidence))),
        risk=_risk(confidence, sample_quality),
        sample_quality=max(0, min(100, int(sample_quality))),
        league_score=league_score,
        status=_status(confidence, sample_quality),
        reason=reason,
    )


def rank_markets(markets: list[MarketDecision]) -> list[dict[str, Any]]:
    ranked = sorted(
        markets,
        key=lambda item: (
            item.status == "🟢 BET",
            item.status == "🟡 PRECAUCIÓN",
            item.confidence,
            item.probability if item.probability is not None else -1,
        ),
        reverse=True,
    )
    return [item.to_dict() for item in ranked]
