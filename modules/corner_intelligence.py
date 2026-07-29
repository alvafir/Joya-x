from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import math

from .utils import clamp


@dataclass
class CornerTeamProfile:
    sample: int
    corners_for: float
    corners_against: float
    total_corners: float
    over_75_rate: float
    over_85_rate: float
    over_95_rate: float
    volatility: float

    def to_dict(self):
        return asdict(self)


@dataclass
class CornerProjection:
    home: CornerTeamProfile
    away: CornerTeamProfile
    home_expected: float
    away_expected: float
    total_expected: float
    sample_quality: float
    confidence: float
    approved: bool
    warnings: List[str]

    def to_dict(self):
        return {
            "home": self.home.to_dict(),
            "away": self.away.to_dict(),
            "home_expected": self.home_expected,
            "away_expected": self.away_expected,
            "total_expected": self.total_expected,
            "sample_quality": self.sample_quality,
            "confidence": self.confidence,
            "approved": self.approved,
            "warnings": self.warnings,
        }


def _stat_value(payload: Dict[str, Any], team_id: int, stat_type: str) -> Optional[float]:
    for team_row in payload.get("response") or []:
        team = team_row.get("team") or {}
        if team.get("id") != team_id:
            continue
        for stat in team_row.get("statistics") or []:
            if stat.get("type") == stat_type:
                value = stat.get("value")
                try:
                    return float(value) if value is not None else None
                except (TypeError, ValueError):
                    return None
    return None


def _profile(batch: Dict[str, Any], team_id: int) -> CornerTeamProfile:
    values_for = []
    values_against = []
    totals = []

    for item in batch.get("items") or []:
        fixture = item.get("fixture") or {}
        statistics = item.get("statistics") or {}
        teams = fixture.get("teams") or {}
        home_id = ((teams.get("home") or {}).get("id"))
        away_id = ((teams.get("away") or {}).get("id"))
        opponent_id = away_id if team_id == home_id else home_id

        own = _stat_value(statistics, team_id, "Corner Kicks")
        opp = _stat_value(statistics, opponent_id, "Corner Kicks") if opponent_id else None
        if own is None or opp is None:
            continue

        values_for.append(own)
        values_against.append(opp)
        totals.append(own + opp)

    n = len(totals)
    if not n:
        return CornerTeamProfile(0, 0, 0, 0, 0, 0, 0, 100)

    mean_total = sum(totals) / n
    variance = sum((x - mean_total) ** 2 for x in totals) / n
    volatility = clamp(math.sqrt(variance) / max(mean_total, 1) * 100)

    return CornerTeamProfile(
        sample=n,
        corners_for=round(sum(values_for) / n, 2),
        corners_against=round(sum(values_against) / n, 2),
        total_corners=round(mean_total, 2),
        over_75_rate=round(sum(x >= 8 for x in totals) / n * 100, 1),
        over_85_rate=round(sum(x >= 9 for x in totals) / n * 100, 1),
        over_95_rate=round(sum(x >= 10 for x in totals) / n * 100, 1),
        volatility=round(volatility, 1),
    )


def build_corner_projection(
    home_batch: Dict[str, Any],
    away_batch: Dict[str, Any],
    home_team_id: int,
    away_team_id: int,
    league_score: float,
) -> CornerProjection:
    home = _profile(home_batch, home_team_id)
    away = _profile(away_batch, away_team_id)
    warnings: List[str] = []

    min_sample = min(home.sample, away.sample)
    total_sample = home.sample + away.sample
    sample_quality = clamp(total_sample / 16 * 100)

    if home.sample < 4:
        warnings.append("Muestra de córners del local inferior a 4 partidos.")
    if away.sample < 4:
        warnings.append("Muestra de córners del visitante inferior a 4 partidos.")

    if min_sample == 0:
        return CornerProjection(
            home=home,
            away=away,
            home_expected=0,
            away_expected=0,
            total_expected=0,
            sample_quality=sample_quality,
            confidence=0,
            approved=False,
            warnings=warnings + ["No existen estadísticas utilizables de córners."],
        )

    # Attack/defence blend: team's corners for + opponent corners conceded.
    home_expected = (home.corners_for * 0.58 + away.corners_against * 0.42)
    away_expected = (away.corners_for * 0.58 + home.corners_against * 0.42)

    # Conservative guardrails.
    home_expected = min(max(home_expected, 1.5), 8.5)
    away_expected = min(max(away_expected, 1.5), 8.5)
    total_expected = home_expected + away_expected

    avg_volatility = (home.volatility + away.volatility) / 2
    confidence = clamp(
        sample_quality * 0.42
        + league_score * 0.24
        + (100 - avg_volatility) * 0.34
    )

    approved = min_sample >= 4 and sample_quality >= 50 and confidence >= 58
    if not approved:
        warnings.append("Corner Engine bloqueado por muestra o confianza insuficiente.")

    return CornerProjection(
        home=home,
        away=away,
        home_expected=round(home_expected, 2),
        away_expected=round(away_expected, 2),
        total_expected=round(total_expected, 2),
        sample_quality=round(sample_quality, 1),
        confidence=round(confidence, 1),
        approved=approved,
        warnings=warnings,
    )
