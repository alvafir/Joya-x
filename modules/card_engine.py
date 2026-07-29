from typing import List
from .models import DataQualityResult, MarketDecision, ProjectionResult
from .market_helpers import no_bet

MARKETS = ['Más de 2.5 tarjetas', 'Más de 3.5 tarjetas', 'Más de 4.5 tarjetas', 'Menos de 6.5 tarjetas', 'Local más de 1.5 tarjetas', 'Visitante más de 1.5 tarjetas', 'Más de 1.5 tarjetas 1T']

def evaluate(projection: ProjectionResult, quality: DataQualityResult, league_score: float = 80.0) -> List[MarketDecision]:
    return [
        no_bet("Cards", market, league_score, quality.score,
               "Mercado incorporado, pero faltan estadísticas específicas suficientes; NO BET.")
        for market in MARKETS
    ]
