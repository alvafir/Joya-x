from __future__ import annotations

from modules.decision_engine import MarketDecision, build_market


def shot_markets(
    source_quality: int,
    league_score: int | None,
) -> list[MarketDecision]:
    markets = []

    for market in ['Remates totales', 'Remates equipo local', 'Remates equipo visitante', 'Tiros al arco equipo local', 'Tiros al arco equipo visitante']:
        markets.append(
            build_market(
                "Shots",
                market,
                None,
                35,
                30,
                league_score,
                "No hay datos suficientes en esta versión. Mercado marcado NO BET.",
            )
        )

    return markets
