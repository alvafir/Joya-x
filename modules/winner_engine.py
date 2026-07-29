from __future__ import annotations

from modules.decision_engine import MarketDecision, build_market


def winner_markets(
    probability: dict,
    source_quality: int,
    league_score: int | None,
) -> list[MarketDecision]:
    home = probability.get("home_percent")
    draw = probability.get("draw_percent")
    away = probability.get("away_percent")

    markets = []

    if all(value is not None for value in [home, draw, away]):
        home_or_draw = min(99, home + draw)
        away_or_draw = min(99, away + draw)

        markets.append(
            build_market(
                "Winner",
                "Doble oportunidad 1X",
                home_or_draw,
                int((home_or_draw + source_quality) / 2),
                source_quality,
                league_score,
                "Derivado de las probabilidades 1X2 disponibles.",
            )
        )

        markets.append(
            build_market(
                "Winner",
                "Doble oportunidad X2",
                away_or_draw,
                int((away_or_draw + source_quality) / 2),
                source_quality,
                league_score,
                "Derivado de las probabilidades 1X2 disponibles.",
            )
        )

        favorite = "Local" if home >= away else "Visitante"
        favorite_probability = max(home, away)

        markets.append(
            build_market(
                "Winner",
                f"Gana {favorite}",
                favorite_probability,
                int((favorite_probability + source_quality) / 2),
                source_quality,
                league_score,
                "Mercado 1X2 basado en la predicción disponible.",
            )
        )

    # First-half winner markets are not available in the current dataset.
    markets.append(
        build_market(
            "Winner",
            "Doble oportunidad primer tiempo",
            None,
            35,
            30,
            league_score,
            "Faltan datos específicos del primer tiempo.",
        )
    )

    markets.append(
        build_market(
            "Winner",
            "Ganador primer tiempo",
            None,
            30,
            25,
            league_score,
            "Faltan datos específicos del primer tiempo.",
        )
    )

    return markets
