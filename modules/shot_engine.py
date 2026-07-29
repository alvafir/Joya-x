from typing import List
from .models import DataQualityResult, MarketDecision, ProjectionResult
from .market_helpers import no_bet

MARKETS = ['Más de 18.5 remates', 'Más de 22.5 remates', 'Más de 6.5 tiros al arco', 'Más de 8.5 tiros al arco', 'Local más de 3.5 tiros al arco', 'Visitante más de 2.5 tiros al arco', 'Porteros más de 5.5 atajadas combinadas']

def evaluate(projection: ProjectionResult, quality: DataQualityResult, league_score: float = 80.0) -> List[MarketDecision]:
    return [
        no_bet("Shots", market, league_score, quality.score,
               "Mercado incorporado, pero faltan estadísticas específicas suficientes; NO BET.")
        for market in MARKETS
    ]
