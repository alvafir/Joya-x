from typing import Any, Dict, Tuple
from .models import ProjectionResult
from .utils import (
    clamp,
    parse_percent,
    poisson_goal_before_probability,
    poisson_no_goal_probability,
    safe_float,
)

def _normalized_probabilities(percent: Dict[str, Any]) -> Tuple[float, float, float]:
    home = parse_percent(percent.get("home")) or 0.0
    draw = parse_percent(percent.get("draw")) or 0.0
    away = parse_percent(percent.get("away")) or 0.0
    total = home + draw + away
    if total <= 0:
        return 0.0, 0.0, 0.0
    return tuple(round(x * 100.0 / total, 2) for x in (home, draw, away))

def build_projection(
    prediction_payload: Dict[str, Any],
    data_quality_score: float,
) -> ProjectionResult:
    response = prediction_payload.get("response") or []
    if not response:
        raise ValueError("No existen predicciones para construir la proyección.")

    row = response[0]
    predictions = row.get("predictions") or {}
    percent = predictions.get("percent") or {}
    home_win, draw, away_win = _normalized_probabilities(percent)

    goals = predictions.get("goals") or {}
    home_xg = safe_float(goals.get("home"))
    away_xg = safe_float(goals.get("away"))
    warnings = []

    if home_xg is None or away_xg is None:
        # Respaldo conservador: solo permite visualización, no inventa precisión alta.
        home_xg = max(0.2, (home_win + 0.5 * draw) / 55.0)
        away_xg = max(0.2, (away_win + 0.5 * draw) / 55.0)
        warnings.append(
            "Goles estimados derivados de probabilidades 1X2 por falta de proyección explícita."
        )

    expected_goals = max(0.0, home_xg + away_xg)
    expected_score = f"{round(home_xg)}-{round(away_xg)}"

    if home_win >= away_win + 15:
        match_script = "Dominio local proyectado"
        first_goal_team = "Local"
    elif away_win >= home_win + 15:
        match_script = "Dominio visitante proyectado"
        first_goal_team = "Visitante"
    else:
        match_script = "Partido equilibrado o de alta incertidumbre"
        first_goal_team = "Indeterminado"

    if expected_goals < 1.7:
        first_goal_window = "31-55"
    elif expected_goals < 2.6:
        first_goal_window = "21-45"
    else:
        first_goal_window = "11-35"

    no_goal_10 = poisson_no_goal_probability(expected_goals, 10)
    no_goal_20 = poisson_no_goal_probability(expected_goals, 20)
    goal_70 = poisson_goal_before_probability(expected_goals, 70)
    goal_80 = poisson_goal_before_probability(expected_goals, 80)

    separation = abs(home_win - away_win)
    projection_confidence = clamp(
        0.55 * data_quality_score
        + 0.25 * max(home_win, draw, away_win)
        + 0.20 * min(100.0, 50.0 + separation)
    )
    if warnings:
        projection_confidence = max(0.0, projection_confidence - 10)

    return ProjectionResult(
        expected_score=expected_score,
        expected_goals=round(expected_goals, 2),
        home_expected_goals=round(home_xg, 2),
        away_expected_goals=round(away_xg, 2),
        home_win=round(home_win, 1),
        draw=round(draw, 1),
        away_win=round(away_win, 1),
        first_goal_team=first_goal_team,
        first_goal_window=first_goal_window,
        no_goal_before_10=round(no_goal_10, 1),
        no_goal_before_20=round(no_goal_20, 1),
        goal_before_70=round(goal_70, 1),
        goal_before_80=round(goal_80, 1),
        match_script=match_script,
        projection_confidence=round(projection_confidence, 1),
        warnings=warnings,
    )
