from typing import Any, Optional
import math
import re

def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))

def parse_percent(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return clamp(float(value))
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return clamp(float(match.group())) if match else None

def safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def poisson_no_goal_probability(expected_goals: float, minute: int) -> float:
    expected_until_minute = max(expected_goals, 0.0) * minute / 90.0
    return clamp(math.exp(-expected_until_minute) * 100.0)

def poisson_goal_before_probability(expected_goals: float, minute: int) -> float:
    return clamp(100.0 - poisson_no_goal_probability(expected_goals, minute))
