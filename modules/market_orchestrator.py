from typing import Dict, List

from .models import DataQualityResult, MarketDecision, ProjectionResult
from .winner_engine import evaluate_winner_markets
from .goal_engine import evaluate_goal_markets
from .corner_engine import evaluate as evaluate_corners
from .card_engine import evaluate as evaluate_cards
from .shot_engine import evaluate as evaluate_shots


def evaluate_all(
    projection: ProjectionResult,
    quality: DataQualityResult,
    league_score: float,
    corner_projection=None,
):
    return {
        "Winner": evaluate_winner_markets(projection, quality, league_score),
        "Goals": evaluate_goal_markets(projection, quality, league_score),
        "Corners": evaluate_corners(
            projection, quality, league_score, corner_projection
        ),
        "Cards": evaluate_cards(projection, quality, league_score),
        "Shots": evaluate_shots(projection, quality, league_score),
    }


def _correlation_group(market: str) -> str:
    m = market.lower()
    if "menos de" in m and "goles ft" in m: return "under_ft"
    if "más de" in m and "goles ft" in m: return "over_ft"
    if "antes del minuto" in m: return "goal_timing"
    if "doble oportunidad" in m: return "double_chance"
    if "dnb" in m: return "dnb"
    if "marca primero" in m: return "first_goal"
    if "rango" in m and "goles" in m: return "goal_range"
    if "ambos marcan" in m: return "btts"
    if "goles 1t" in m: return "goals_1h"
    if "córners" in m and "más de" in m and not ("local" in m or "visitante" in m):
        return "corners_over"
    if "córners" in m and "menos de" in m:
        return "corners_under"
    if "rango" in m and "córners" in m:
        return "corner_range"
    if "tendrá más córners" in m:
        return "corner_winner"
    return m


def global_ranking(
    engines: Dict[str, List[MarketDecision]],
    limit: int = 20,
) -> List[MarketDecision]:
    candidates = sorted(
        [m for values in engines.values() for m in values],
        key=lambda x: x.joya_score,
        reverse=True,
    )
    selected = []
    group_counts = {}
    family_counts = {}

    for market in candidates:
        group = _correlation_group(market.market)
        family = market.family
        if group_counts.get(group, 0) >= 2:
            continue
        if family_counts.get(family, 0) >= 5:
            continue
        selected.append(market)
        group_counts[group] = group_counts.get(group, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
        if len(selected) >= limit:
            break

    return selected
