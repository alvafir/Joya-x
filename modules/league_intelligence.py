from __future__ import annotations

import pandas as pd


LOW_QUALITY_TERMS = {
    "friendly",
    "friendlies",
    "amistoso",
    "amistosos",
    "u17",
    "u18",
    "u19",
    "u20",
    "u21",
    "reserve",
    "reserves",
    "youth",
    "women friendly",
}


def _contains_term(text: str, terms: set[str]) -> bool:
    normalized = (text or "").lower()
    return any(term in normalized for term in terms)


def calculate_league_score(
    country: str,
    league: str,
    matches: int,
    coverage: str,
) -> int:
    text = f"{country} {league}".lower()
    score = 50

    if "🟢" in coverage:
        score += 25
    elif "🟡" in coverage:
        score += 10
    else:
        score -= 20

    if matches >= 8:
        score += 15
    elif matches >= 4:
        score += 10
    elif matches >= 2:
        score += 5

    if _contains_term(text, LOW_QUALITY_TERMS):
        score -= 35

    if any(
        keyword in text
        for keyword in {
            "premier",
            "primera",
            "serie a",
            "liga profesional",
            "mls",
            "bundesliga",
            "la liga",
            "ligue 1",
        }
    ):
        score += 10

    return max(0, min(100, score))


def classify_league(score: int) -> tuple[str, str]:
    if score >= 85:
        return "🟢 RECOMENDADA", "Alta"
    if score >= 70:
        return "🟡 OBSERVAR", "Media"
    return "🔴 EVITAR", "Baja"


def enrich_league_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if summary is None or summary.empty:
        return pd.DataFrame()

    required = {"País", "Liga", "Partidos", "Cobertura"}

    if not required.issubset(summary.columns):
        return pd.DataFrame()

    enriched = summary.copy()

    enriched["League Score"] = enriched.apply(
        lambda row: calculate_league_score(
            str(row["País"]),
            str(row["Liga"]),
            int(row["Partidos"]),
            str(row["Cobertura"]),
        ),
        axis=1,
    )

    classifications = enriched["League Score"].apply(classify_league)
    enriched["Estado"] = classifications.apply(lambda item: item[0])
    enriched["Prioridad"] = classifications.apply(lambda item: item[1])

    return enriched.sort_values(
        ["League Score", "Partidos"],
        ascending=[False, False],
    ).reset_index(drop=True)


def filter_leagues(
    frame: pd.DataFrame,
    recommended_only: bool,
    exclude_friendlies: bool,
    exclude_youth: bool,
    minimum_matches: int,
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()

    filtered = frame.copy()

    if recommended_only:
        filtered = filtered[filtered["League Score"] >= 85]

    if minimum_matches > 1:
        filtered = filtered[filtered["Partidos"] >= minimum_matches]

    text = (
        filtered["País"].astype(str)
        + " "
        + filtered["Liga"].astype(str)
    ).str.lower()

    if exclude_friendlies:
        filtered = filtered[
            ~text.str.contains("friendly|friendlies|amistoso", regex=True)
        ]

    if exclude_youth:
        filtered = filtered[
            ~text.str.contains(
                "u17|u18|u19|u20|u21|youth|reserve|reserves",
                regex=True,
            )
        ]

    return filtered.reset_index(drop=True)
