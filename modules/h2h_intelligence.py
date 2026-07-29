from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import math

from .utils import clamp


@dataclass
class H2HReport:
    available: bool
    sample: int
    weighted_sample: float
    score: float
    confidence: float
    weight_label: str
    home_win_rate: float
    draw_rate: float
    away_win_rate: float
    avg_goals: float
    btts_rate: float
    over_15_rate: float
    over_25_rate: float
    under_35_rate: float
    avg_corners: Optional[float]
    first_goal_avg_minute: Optional[float]
    latest_match_age_days: Optional[int]
    reasons: List[str]
    warnings: List[str]

    def to_dict(self):
        return asdict(self)


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _time_weight(match_date: Optional[datetime]) -> float:
    if match_date is None:
        return 0.45

    age_days = max(0, (datetime.now(timezone.utc) - match_date).days)
    age_years = age_days / 365.25

    # Exponential decay with a conservative floor.
    return max(0.15, math.exp(-0.28 * age_years))


def _stat_value(payload: Dict[str, Any], team_id: int, stat_type: str) -> Optional[float]:
    for row in payload.get("response") or []:
        team = row.get("team") or {}
        if team.get("id") != team_id:
            continue
        for stat in row.get("statistics") or []:
            if stat.get("type") == stat_type:
                try:
                    value = stat.get("value")
                    return float(value) if value is not None else None
                except (TypeError, ValueError):
                    return None
    return None


def _first_goal_minute(events_payload: Dict[str, Any]) -> Optional[float]:
    minutes = []
    for event in events_payload.get("response") or []:
        if str(event.get("type") or "").lower() != "goal":
            continue
        time_data = event.get("time") or {}
        elapsed = time_data.get("elapsed")
        extra = time_data.get("extra") or 0
        try:
            minutes.append(float(elapsed) + float(extra))
        except (TypeError, ValueError):
            continue
    return min(minutes) if minutes else None


def build_h2h_report(
    enriched_batch: Dict[str, Any],
    home_team_id: int,
    away_team_id: int,
) -> H2HReport:
    items = enriched_batch.get("items") or []
    warnings = list(enriched_batch.get("warnings") or [])
    reasons: List[str] = []

    if not items:
        return H2HReport(
            available=False,
            sample=0,
            weighted_sample=0.0,
            score=0.0,
            confidence=0.0,
            weight_label="Sin peso",
            home_win_rate=0.0,
            draw_rate=0.0,
            away_win_rate=0.0,
            avg_goals=0.0,
            btts_rate=0.0,
            over_15_rate=0.0,
            over_25_rate=0.0,
            under_35_rate=0.0,
            avg_corners=None,
            first_goal_avg_minute=None,
            latest_match_age_days=None,
            reasons=["No existe H2H utilizable."],
            warnings=warnings,
        )

    weighted_home = weighted_draw = weighted_away = 0.0
    weighted_goals = weighted_btts = weighted_o15 = weighted_o25 = weighted_u35 = 0.0
    total_weight = 0.0
    corner_values = []
    first_goal_values = []
    latest_age = None
    used = 0

    for item in items:
        fixture_row = item.get("fixture") or {}
        fixture = fixture_row.get("fixture") or {}
        teams = fixture_row.get("teams") or {}
        goals = fixture_row.get("goals") or {}

        gh = goals.get("home")
        ga = goals.get("away")
        if gh is None or ga is None:
            continue

        try:
            gh = float(gh)
            ga = float(ga)
        except (TypeError, ValueError):
            continue

        fixture_home_id = ((teams.get("home") or {}).get("id"))
        fixture_away_id = ((teams.get("away") or {}).get("id"))
        dt = _parse_date(fixture.get("date"))
        weight = _time_weight(dt)

        if dt:
            age_days = max(0, (datetime.now(timezone.utc) - dt).days)
            latest_age = age_days if latest_age is None else min(latest_age, age_days)

        if fixture_home_id == home_team_id and fixture_away_id == away_team_id:
            home_goals, away_goals = gh, ga
        elif fixture_home_id == away_team_id and fixture_away_id == home_team_id:
            home_goals, away_goals = ga, gh
        else:
            continue

        total = home_goals + away_goals
        used += 1
        total_weight += weight
        weighted_home += weight * int(home_goals > away_goals)
        weighted_draw += weight * int(home_goals == away_goals)
        weighted_away += weight * int(away_goals > home_goals)
        weighted_goals += weight * total
        weighted_btts += weight * int(home_goals > 0 and away_goals > 0)
        weighted_o15 += weight * int(total > 1.5)
        weighted_o25 += weight * int(total > 2.5)
        weighted_u35 += weight * int(total < 3.5)

        stats = item.get("statistics") or {}
        c_home = _stat_value(stats, fixture_home_id, "Corner Kicks") if fixture_home_id else None
        c_away = _stat_value(stats, fixture_away_id, "Corner Kicks") if fixture_away_id else None
        if c_home is not None and c_away is not None:
            corner_values.append(c_home + c_away)

        first_goal = _first_goal_minute(item.get("events") or {})
        if first_goal is not None:
            first_goal_values.append(first_goal)

    if used == 0 or total_weight <= 0:
        return H2HReport(
            available=False,
            sample=0,
            weighted_sample=0.0,
            score=0.0,
            confidence=0.0,
            weight_label="Sin peso",
            home_win_rate=0.0,
            draw_rate=0.0,
            away_win_rate=0.0,
            avg_goals=0.0,
            btts_rate=0.0,
            over_15_rate=0.0,
            over_25_rate=0.0,
            under_35_rate=0.0,
            avg_corners=None,
            first_goal_avg_minute=None,
            latest_match_age_days=latest_age,
            reasons=["Los H2H devueltos no fueron utilizables."],
            warnings=warnings,
        )

    sample_score = clamp(used / 8 * 100)
    recency_score = clamp((total_weight / used) * 100)
    coverage_score = clamp(
        60
        + (20 if corner_values else 0)
        + (20 if first_goal_values else 0)
    )
    score = clamp(
        sample_score * 0.45
        + recency_score * 0.35
        + coverage_score * 0.20
    )
    confidence = clamp(score * 0.82 + min(used, 8) / 8 * 18)

    if score >= 78:
        weight_label = "Alto"
    elif score >= 55:
        weight_label = "Medio"
    elif score >= 30:
        weight_label = "Bajo"
    else:
        weight_label = "Muy bajo"

    if used >= 5:
        reasons.append("Muestra H2H suficiente para aportar contexto.")
    else:
        reasons.append("Muestra H2H limitada; peso reducido.")
    if latest_age is not None and latest_age > 1800:
        reasons.append("Los enfrentamientos son antiguos; se aplicó decaimiento temporal.")
    if corner_values:
        reasons.append("H2H incluye cobertura real de córners.")
    if first_goal_values:
        reasons.append("H2H incluye eventos para estimar primer gol.")

    return H2HReport(
        available=True,
        sample=used,
        weighted_sample=round(total_weight, 2),
        score=round(score, 1),
        confidence=round(confidence, 1),
        weight_label=weight_label,
        home_win_rate=round(weighted_home / total_weight * 100, 1),
        draw_rate=round(weighted_draw / total_weight * 100, 1),
        away_win_rate=round(weighted_away / total_weight * 100, 1),
        avg_goals=round(weighted_goals / total_weight, 2),
        btts_rate=round(weighted_btts / total_weight * 100, 1),
        over_15_rate=round(weighted_o15 / total_weight * 100, 1),
        over_25_rate=round(weighted_o25 / total_weight * 100, 1),
        under_35_rate=round(weighted_u35 / total_weight * 100, 1),
        avg_corners=round(sum(corner_values) / len(corner_values), 2) if corner_values else None,
        first_goal_avg_minute=round(sum(first_goal_values) / len(first_goal_values), 1) if first_goal_values else None,
        latest_match_age_days=latest_age,
        reasons=reasons,
        warnings=warnings,
    )
