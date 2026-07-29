from __future__ import annotations

from modules.card_engine import card_markets
from modules.corner_engine import corner_markets
from modules.decision_engine import rank_markets
from modules.goal_engine import goal_markets
from modules.shot_engine import shot_markets
from modules.winner_engine import winner_markets


def run_decision_engine(
    parsed_probability: dict,
    league_score: int | None = None,
) -> list[dict]:
    source_quality = 40

    if parsed_probability.get("data_complete"):
        source_quality += 25

    if parsed_probability.get("comparison"):
        source_quality += 15

    if parsed_probability.get("advice"):
        source_quality += 10

    source_quality = min(100, source_quality)

    markets = []
    markets.extend(
        winner_markets(
            parsed_probability,
            source_quality,
            league_score,
        )
    )
    markets.extend(
        goal_markets(
            parsed_probability,
            source_quality,
            league_score,
        )
    )
    markets.extend(
        corner_markets(source_quality, league_score)
    )
    markets.extend(
        card_markets(source_quality, league_score)
    )
    markets.extend(
        shot_markets(source_quality, league_score)
    )

    return rank_markets(markets)
