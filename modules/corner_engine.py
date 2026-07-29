from __future__ import annotations

from modules.decision_engine import MarketDecision, build_market


def corner_markets(
    source_quality: int,
    league_score: int | None,
) -> list[MarketDecision]:
    markets = []

    for market in ['Corners totales', 'Corners equipo local', 'Corners equipo visitante']:
        markets.append(
            build_market(
                "Corners",
                market,
                None,
                35,
                30,
                league_score,
                "No hay datos suficientes en esta versión. Mercado marcado NO BET.",
            )
        )

    return markets
