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
) -> Dict[str, List[MarketDecision]]:
    engines = {
        "Winner": evaluate_winner_markets(projection, quality, league_score),
        "Goals": evaluate_goal_markets(projection, quality, league_score),
        "Corners": evaluate_corners(projection, quality, league_score),
        "Cards": evaluate_cards(projection, quality, league_score),
        "Shots": evaluate_shots(projection, quality, league_score),
    }
    return engines

def global_ranking(engines: Dict[str, List[MarketDecision]]) -> List[MarketDecision]:
    all_markets = [m for values in engines.values() for m in values]
    return sorted(all_markets, key=lambda x: x.joya_score, reverse=True)
