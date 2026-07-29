from dataclasses import dataclass, asdict
from typing import Any, Dict, List

@dataclass
class DataQualityResult:
    score: float
    status: str
    approved: bool
    sample_quality: str
    reasons: List[str]
    checks: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ProjectionResult:
    expected_score: str
    expected_goals: float
    home_expected_goals: float
    away_expected_goals: float
    home_win: float
    draw: float
    away_win: float
    first_goal_team: str
    first_goal_window: str
    no_goal_before_10: float
    no_goal_before_20: float
    goal_before_70: float
    goal_before_80: float
    match_script: str
    projection_confidence: float
    projection_source: str
    source_quality: float
    sample_home: int
    sample_away: int
    sample_h2h: int
    inputs: Dict[str, Any]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MarketDecision:
    family: str
    market: str
    probability: float
    confidence: float
    risk: str
    league_score: float
    data_quality: float
    joya_score: float
    status: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
