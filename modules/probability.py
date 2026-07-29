from __future__ import annotations


def _to_number(value) -> int | None:
    if value is None:
        return None

    text = str(value).strip().replace("%", "")

    try:
        return int(round(float(text)))
    except (TypeError, ValueError):
        return None


def parse_prediction(payload: dict) -> dict:
    """
    Convierte la respuesta oficial de API-Football en un formato
    estable para Streamlit. No inventa valores faltantes.
    """
    if not isinstance(payload, dict):
        return {}

    predictions = payload.get("predictions", {}) or {}
    percent = predictions.get("percent", {}) or {}
    advice = predictions.get("advice") or "Sin recomendación"
    winner = predictions.get("winner") or {}

    teams = payload.get("teams", {}) or {}
    comparison = payload.get("comparison", {}) or {}

    result = {
        "home_percent": _to_number(percent.get("home")),
        "draw_percent": _to_number(percent.get("draw")),
        "away_percent": _to_number(percent.get("away")),
        "advice": advice,
        "winner_name": winner.get("name") or "Sin favorito",
        "winner_comment": winner.get("comment") or "",
        "home_team": ((teams.get("home") or {}).get("name") or ""),
        "away_team": ((teams.get("away") or {}).get("name") or ""),
        "comparison": comparison,
    }

    available = [
        result["home_percent"],
        result["draw_percent"],
        result["away_percent"],
    ]

    result["data_complete"] = all(value is not None for value in available)
    result["max_probability"] = max(
        [value for value in available if value is not None],
        default=None,
    )

    return result
