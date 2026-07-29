from dataclasses import dataclass, asdict
from typing import Any, Dict, List
from .utils import clamp, poisson_goal_before_probability, poisson_no_goal_probability
from .models import ProjectionResult
from .intelligence_hub import IntelligenceReport


@dataclass
class Scenario:
    name: str
    home_goals: float
    away_goals: float
    total_goals: float
    score: str

    def to_dict(self):
        return asdict(self)


@dataclass
class ProjectionV3:
    base: ProjectionResult
    conservative: Scenario
    central: Scenario
    offensive: Scenario
    uncertainty: float
    stability: float
    narrative: str
    warnings: List[str]

    def to_dict(self):
        return {
            "base": self.base.to_dict(),
            "conservative": self.conservative.to_dict(),
            "central": self.central.to_dict(),
            "offensive": self.offensive.to_dict(),
            "uncertainty": self.uncertainty,
            "stability": self.stability,
            "narrative": self.narrative,
            "warnings": self.warnings,
        }


def build_projection_v3(
    base: ProjectionResult,
    intelligence: IntelligenceReport,
) -> ProjectionV3:
    warnings = list(base.warnings) + list(intelligence.warnings)

    h_recent = intelligence.home_10.goals_for
    a_recent = intelligence.away_10.goals_for
    h_concede = intelligence.home_10.goals_against
    a_concede = intelligence.away_10.goals_against

    h_split = intelligence.home_split["goals_for"] or h_recent
    a_split = intelligence.away_split["goals_for"] or a_recent
    h_split_concede = intelligence.home_split["goals_against"] or h_concede
    a_split_concede = intelligence.away_split["goals_against"] or a_concede

    # Central blends prior projection with recent and venue form.
    central_h = (
        base.home_expected_goals * 0.45
        + ((h_recent + a_concede) / 2) * 0.25
        + ((h_split + a_split_concede) / 2) * 0.30
    )
    central_a = (
        base.away_expected_goals * 0.45
        + ((a_recent + h_concede) / 2) * 0.25
        + ((a_split + h_split_concede) / 2) * 0.30
    )

    central_h = min(max(central_h, 0.2), 3.8)
    central_a = min(max(central_a, 0.2), 3.8)

    volatility_factor = intelligence.volatility / 100
    conservative_h = max(0.15, central_h * (0.82 - volatility_factor * 0.08))
    conservative_a = max(0.15, central_a * (0.82 - volatility_factor * 0.08))
    offensive_h = min(4.2, central_h * (1.18 + volatility_factor * 0.10))
    offensive_a = min(4.2, central_a * (1.18 + volatility_factor * 0.10))

    central_total = central_h + central_a
    uncertainty = clamp(
        intelligence.volatility * 0.52
        + (100 - intelligence.coverage) * 0.28
        + (100 - base.source_quality) * 0.20
    )
    stability = clamp(100 - uncertainty)

    if uncertainty >= 65:
        narrative = "Partido de alta incertidumbre; priorizar líneas amplias o NO BET."
    elif central_total >= 2.8:
        narrative = "Escenario central ofensivo, con mayor probabilidad de goles durante ambos tiempos."
    elif central_total <= 1.9:
        narrative = "Escenario central cerrado, con ritmo goleador moderado o bajo."
    else:
        narrative = "Escenario equilibrado, con proyección de goles intermedia."

    # Replace core temporal outputs with central scenario.
    base.home_expected_goals = round(central_h, 2)
    base.away_expected_goals = round(central_a, 2)
    base.expected_goals = round(central_total, 2)
    base.expected_score = f"{round(central_h)}-{round(central_a)}"
    base.no_goal_before_10 = round(poisson_no_goal_probability(central_total, 10), 1)
    base.no_goal_before_20 = round(poisson_no_goal_probability(central_total, 20), 1)
    base.goal_before_70 = round(poisson_goal_before_probability(central_total, 70), 1)
    base.goal_before_80 = round(poisson_goal_before_probability(central_total, 80), 1)
    base.projection_confidence = round(
        clamp(base.projection_confidence * 0.62 + stability * 0.38), 1
    )

    return ProjectionV3(
        base=base,
        conservative=Scenario(
            "Conservador",
            round(conservative_h, 2),
            round(conservative_a, 2),
            round(conservative_h + conservative_a, 2),
            f"{round(conservative_h)}-{round(conservative_a)}",
        ),
        central=Scenario(
            "Central",
            round(central_h, 2),
            round(central_a, 2),
            round(central_total, 2),
            f"{round(central_h)}-{round(central_a)}",
        ),
        offensive=Scenario(
            "Ofensivo",
            round(offensive_h, 2),
            round(offensive_a, 2),
            round(offensive_h + offensive_a, 2),
            f"{round(offensive_h)}-{round(offensive_a)}",
        ),
        uncertainty=round(uncertainty, 1),
        stability=round(stability, 1),
        narrative=narrative,
        warnings=warnings,
    )
