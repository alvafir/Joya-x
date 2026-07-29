from typing import Any, Dict, List
from .models import DataQualityResult
from .utils import parse_percent, safe_float, clamp

MIN_APPROVAL_SCORE = 70.0

def evaluate_data_quality(
    fixture: Dict[str, Any],
    prediction_payload: Dict[str, Any],
    league_score: float = 80.0,
) -> DataQualityResult:
    reasons: List[str] = []
    response = prediction_payload.get("response") or []
    prediction_row = response[0] if response else {}
    predictions = prediction_row.get("predictions") or {}
    comparison = prediction_row.get("comparison") or {}

    fixture_id = ((fixture.get("fixture") or {}).get("id"))
    teams = fixture.get("teams") or {}
    has_teams = bool((teams.get("home") or {}).get("name")) and bool(
        (teams.get("away") or {}).get("name")
    )
    has_prediction = bool(predictions)
    percent = predictions.get("percent") or {}
    has_1x2 = all(parse_percent(percent.get(k)) is not None for k in ("home", "draw", "away"))

    goals = predictions.get("goals") or {}
    has_goal_projection = (
        safe_float(goals.get("home")) is not None
        and safe_float(goals.get("away")) is not None
    )
    has_comparison = bool(comparison)
    league_ok = league_score >= 60

    checks = {
        "fixture_id": bool(fixture_id),
        "teams": has_teams,
        "prediction": has_prediction,
        "probabilities_1x2": has_1x2,
        "goal_projection": has_goal_projection,
        "comparison": has_comparison,
        "league_score": league_ok,
    }

    weights = {
        "fixture_id": 8,
        "teams": 12,
        "prediction": 22,
        "probabilities_1x2": 25,
        "goal_projection": 15,
        "comparison": 10,
        "league_score": 8,
    }
    score = sum(weights[k] for k, ok in checks.items() if ok)
    score = clamp(score)

    for key, ok in checks.items():
        if not ok:
            reasons.append(f"Falta o no supera el control: {key.replace('_', ' ')}.")

    approved = score >= MIN_APPROVAL_SCORE and has_1x2 and has_prediction
    if score >= 90:
        sample_quality = "Alta"
        status = "APROBADO"
    elif score >= MIN_APPROVAL_SCORE:
        sample_quality = "Media"
        status = "APROBADO CON RESERVAS"
    else:
        sample_quality = "Baja"
        status = "NO BET"

    if approved and not reasons:
        reasons.append("Datos esenciales disponibles y consistentes.")
    elif not approved:
        reasons.append("Los motores de mercado quedan bloqueados.")

    return DataQualityResult(
        score=round(score, 1),
        status=status,
        approved=approved,
        sample_quality=sample_quality,
        reasons=reasons,
        checks=checks,
    )
