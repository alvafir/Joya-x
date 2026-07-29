from __future__ import annotations

from modules.decision_engine import MarketDecision, build_market


def goal_markets(
    probability: dict,
    source_quality: int,
    league_score: int | None,
) -> list[MarketDecision]:
    advice = str(probability.get("advice") or "").lower()
    markets = []

    inferred = {
        "Under 3.5 goles": 78 if "under" in advice else None,
        "Over 1.5 goles": 76 if "over" in advice else None,
        "Gol antes del minuto 80": None,
        "Gol antes del minuto 70": None,
        "Ningún gol antes del minuto 10": None,
        "Ningún gol antes del minuto 20": None,
        "Menos de 1.5 goles primer tiempo": None,
        "Menos de 2.5 goles primer tiempo": None,
        "Equipo local +0.5 goles": None,
        "Equipo visitante +0.5 goles": None,
    }

    for market, value in inferred.items():
        if value is None:
            markets.append(
                build_market(
                    "Goals",
                    market,
                    None,
                    40,
                    35,
                    league_score,
                    "Faltan estadísticas específicas para este mercado.",
                )
            )
        else:
            markets.append(
                build_market(
                    "Goals",
                    market,
                    value,
                    int((value + source_quality) / 2),
                    source_quality,
                    league_score,
                    "Inferencia limitada desde el consejo de API-Football.",
                )
            )

    return markets
