from typing import Any, Dict, List, Optional, Tuple
import math

from .models import ProjectionResult
from .utils import clamp, parse_percent, poisson_goal_before_probability, poisson_no_goal_probability, safe_float

def _normalized_probabilities(percent: Dict[str, Any]) -> Tuple[float, float, float]:
    vals = [parse_percent(percent.get(k)) or 0.0 for k in ("home", "draw", "away")]
    total = sum(vals)
    if total <= 0:
        return 33.3, 33.4, 33.3
    return tuple(round(v * 100 / total, 2) for v in vals)

def _completed_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for item in payload.get("response") or []:
        goals = item.get("goals") or {}
        if safe_float(goals.get("home")) is None or safe_float(goals.get("away")) is None:
            continue
        rows.append(item)
    return rows

def _team_stats(payload: Dict[str, Any], team_id: int) -> Dict[str, Any]:
    rows = _completed_rows(payload)
    gf = ga = 0.0
    home_gf = home_ga = away_gf = away_ga = 0.0
    home_n = away_n = 0
    wins = draws = losses = 0

    for item in rows:
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        home_id = ((teams.get("home") or {}).get("id"))
        away_id = ((teams.get("away") or {}).get("id"))
        gh = float(goals.get("home"))
        ga_ = float(goals.get("away"))

        if team_id == home_id:
            scored, conceded = gh, ga_
            home_gf += scored; home_ga += conceded; home_n += 1
        elif team_id == away_id:
            scored, conceded = ga_, gh
            away_gf += scored; away_ga += conceded; away_n += 1
        else:
            continue

        gf += scored; ga += conceded
        if scored > conceded: wins += 1
        elif scored == conceded: draws += 1
        else: losses += 1

    n = wins + draws + losses
    return {
        "n": n,
        "gf_avg": gf / n if n else None,
        "ga_avg": ga / n if n else None,
        "home_n": home_n,
        "home_gf_avg": home_gf / home_n if home_n else None,
        "home_ga_avg": home_ga / home_n if home_n else None,
        "away_n": away_n,
        "away_gf_avg": away_gf / away_n if away_n else None,
        "away_ga_avg": away_ga / away_n if away_n else None,
        "win_rate": wins / n * 100 if n else None,
        "draw_rate": draws / n * 100 if n else None,
        "loss_rate": losses / n * 100 if n else None,
    }

def _h2h_stats(payload: Dict[str, Any], home_team_id: int, away_team_id: int) -> Dict[str, Any]:
    rows = _completed_rows(payload)
    total_goals = home_goals = away_goals = 0.0
    n = 0
    for item in rows:
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        hid = ((teams.get("home") or {}).get("id"))
        aid = ((teams.get("away") or {}).get("id"))
        gh = float(goals.get("home")); ga = float(goals.get("away"))
        if hid == home_team_id and aid == away_team_id:
            home_goals += gh; away_goals += ga
        elif hid == away_team_id and aid == home_team_id:
            home_goals += ga; away_goals += gh
        else:
            continue
        total_goals += gh + ga
        n += 1
    return {
        "n": n,
        "total_avg": total_goals / n if n else None,
        "home_avg": home_goals / n if n else None,
        "away_avg": away_goals / n if n else None,
    }

def _valid_api_goals(predictions: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    goals = predictions.get("goals") or {}
    h = safe_float(goals.get("home"))
    a = safe_float(goals.get("away"))
    if h is None or a is None:
        return None, None
    # 0-0 is treated as unavailable, not as a real model projection.
    if h <= 0 and a <= 0:
        return None, None
    if h < 0 or a < 0 or h + a > 8:
        return None, None
    return h, a

def build_projection_v2(
    prediction_payload: Dict[str, Any],
    home_recent_payload: Dict[str, Any],
    away_recent_payload: Dict[str, Any],
    h2h_payload: Dict[str, Any],
    home_team_id: int,
    away_team_id: int,
    data_quality_score: float,
) -> ProjectionResult:
    response = prediction_payload.get("response") or []
    row = response[0] if response else {}
    predictions = row.get("predictions") or {}
    percent = predictions.get("percent") or {}
    home_win, draw, away_win = _normalized_probabilities(percent)

    home_stats = _team_stats(home_recent_payload, home_team_id)
    away_stats = _team_stats(away_recent_payload, away_team_id)
    h2h = _h2h_stats(h2h_payload, home_team_id, away_team_id)
    warnings: List[str] = []

    api_h, api_a = _valid_api_goals(predictions)
    components_home = []
    components_away = []

    # Local/visitor split receives the greatest weight when available.
    if home_stats["home_gf_avg"] is not None and away_stats["away_ga_avg"] is not None:
        components_home.append(((home_stats["home_gf_avg"] + away_stats["away_ga_avg"]) / 2, 0.40))
    if away_stats["away_gf_avg"] is not None and home_stats["home_ga_avg"] is not None:
        components_away.append(((away_stats["away_gf_avg"] + home_stats["home_ga_avg"]) / 2, 0.40))

    # General form.
    if home_stats["gf_avg"] is not None and away_stats["ga_avg"] is not None:
        components_home.append(((home_stats["gf_avg"] + away_stats["ga_avg"]) / 2, 0.28))
    if away_stats["gf_avg"] is not None and home_stats["ga_avg"] is not None:
        components_away.append(((away_stats["gf_avg"] + home_stats["ga_avg"]) / 2, 0.28))

    # H2H.
    if h2h["home_avg"] is not None:
        components_home.append((h2h["home_avg"], 0.12))
    if h2h["away_avg"] is not None:
        components_away.append((h2h["away_avg"], 0.12))

    # API goals when genuinely available.
    if api_h is not None and api_a is not None:
        components_home.append((api_h, 0.20))
        components_away.append((api_a, 0.20))

    def weighted(parts):
        if not parts:
            return None
        w = sum(weight for _, weight in parts)
        return sum(value * weight for value, weight in parts) / w if w else None

    home_xg = weighted(components_home)
    away_xg = weighted(components_away)
    source = "Forma + local/visita + H2H"
    if api_h is not None:
        source += " + API"

    # Final conservative fallback from 1X2 only.
    if home_xg is None or away_xg is None:
        warnings.append("Muestra estadística incompleta; se aplicó respaldo conservador 1X2.")
        base_total = 2.25
        strength_home = max(0.15, home_win + draw * 0.35)
        strength_away = max(0.15, away_win + draw * 0.35)
        denom = strength_home + strength_away
        home_xg = base_total * strength_home / denom
        away_xg = base_total * strength_away / denom
        source = "Respaldo conservador 1X2"

    # Guardrails.
    home_xg = min(max(home_xg, 0.20), 3.80)
    away_xg = min(max(away_xg, 0.20), 3.80)
    total = home_xg + away_xg

    sample_home = home_stats["n"]
    sample_away = away_stats["n"]
    sample_h2h = h2h["n"]
    sample_score = clamp(min(sample_home, 10) * 4 + min(sample_away, 10) * 4 + min(sample_h2h, 5) * 4)
    source_quality = clamp(0.55 * data_quality_score + 0.45 * sample_score)

    if min(sample_home, sample_away) < 5:
        warnings.append("Uno de los equipos tiene menos de cinco partidos utilizables.")
    if sample_h2h == 0:
        warnings.append("Sin H2H utilizable; no se penaliza de forma crítica.")

    expected_score = f"{round(home_xg)}-{round(away_xg)}"
    if home_win >= away_win + 15:
        script = "Dominio local proyectado"
        first_goal_team = "Local"
    elif away_win >= home_win + 15:
        script = "Dominio visitante proyectado"
        first_goal_team = "Visitante"
    else:
        script = "Partido equilibrado o de incertidumbre media"
        first_goal_team = "Indeterminado"

    first_goal_window = "31-55" if total < 1.7 else ("21-45" if total < 2.7 else "11-35")
    no10 = poisson_no_goal_probability(total, 10)
    no20 = poisson_no_goal_probability(total, 20)
    g70 = poisson_goal_before_probability(total, 70)
    g80 = poisson_goal_before_probability(total, 80)

    separation = abs(home_win - away_win)
    confidence = clamp(
        source_quality * 0.48
        + data_quality_score * 0.22
        + max(home_win, draw, away_win) * 0.18
        + min(100, 50 + separation) * 0.12
    )
    if source == "Respaldo conservador 1X2":
        confidence = min(confidence, 72.0)

    return ProjectionResult(
        expected_score=expected_score,
        expected_goals=round(total, 2),
        home_expected_goals=round(home_xg, 2),
        away_expected_goals=round(away_xg, 2),
        home_win=round(home_win, 1),
        draw=round(draw, 1),
        away_win=round(away_win, 1),
        first_goal_team=first_goal_team,
        first_goal_window=first_goal_window,
        no_goal_before_10=round(no10, 1),
        no_goal_before_20=round(no20, 1),
        goal_before_70=round(g70, 1),
        goal_before_80=round(g80, 1),
        match_script=script,
        projection_confidence=round(confidence, 1),
        projection_source=source,
        source_quality=round(source_quality, 1),
        sample_home=sample_home,
        sample_away=sample_away,
        sample_h2h=sample_h2h,
        inputs={
            "home_stats": home_stats,
            "away_stats": away_stats,
            "h2h": h2h,
            "api_goals": {"home": api_h, "away": api_a},
        },
        warnings=warnings,
    )
