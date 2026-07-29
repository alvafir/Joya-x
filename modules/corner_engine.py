from typing import List
from .models import DataQualityResult, MarketDecision, ProjectionResult
from .market_helpers import no_bet

MARKETS = ['Más de 7.5 córners', 'Más de 8.5 córners', 'Más de 9.5 córners', 'Menos de 11.5 córners', 'Más córners local', 'Más córners visitante', 'Más de 3.5 córners 1T']

def evaluate(projection: ProjectionResult, quality: DataQualityResult, league_score: float = 80.0) -> List[MarketDecision]:
    return [
        no_bet("Corners", market, league_score, quality.score,
               "Mercado incorporado, pero faltan estadísticas específicas suficientes; NO BET.")
        for market in MARKETS
    ]
