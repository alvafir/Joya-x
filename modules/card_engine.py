from __future__ import annotations

from modules.decision_engine import MarketDecision, build_market


def card_markets(
    source_quality: int,
    league_score: int | None,
) -> list[MarketDecision]:
    markets = []

    for market in ['Tarjetas totales', 'Tarjetas equipo local', 'Tarjetas equipo visitante']:
        markets.append(
            build_market(
                "Cards",
                market,
                None,
                35,
                30,
                league_score,
                "No hay datos suficientes en esta versión. Mercado marcado NO BET.",
            )
        )

    return markets
