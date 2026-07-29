from typing import Optional
from .h2h_intelligence import H2HReport
from .utils import clamp


def effective_weight(report: Optional[H2HReport], max_weight: float = 0.16) -> float:
    if report is None or not report.available:
        return 0.0
    return max_weight * clamp(report.score) / 100.0


def blend_probability(
    base_probability: float,
    h2h_probability: float,
    report: Optional[H2HReport],
    max_weight: float = 0.16,
) -> float:
    weight = effective_weight(report, max_weight)
    return clamp(base_probability * (1 - weight) + h2h_probability * weight)


def h2h_reason(report: Optional[H2HReport], metric: str, value: float) -> str:
    if report is None or not report.available:
        return ""
    return (
        f" H2H ({report.sample} partidos, peso {report.weight_label}) "
        f"aporta {metric}: {value:.1f}%."
    )
