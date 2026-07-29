from __future__ import annotations

from collections import defaultdict

import pandas as pd

from modules.api import get_fixtures_by_date


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
    "reserves",
    "reserve",
    "youth",
}


def _coverage_label(league_name: str, country: str) -> str:
    text = f"{league_name} {country}".lower()

    if any(term in text for term in LOW_QUALITY_TERMS):
        return "🔴 Volátil"

    if any(term in text for term in {"premier", "liga", "serie", "mls", "bundesliga"}):
        return "🟢 Buena"

    return "🟡 Media"


def scan_fixtures(date_iso: str) -> dict:
    result = get_fixtures_by_date(date_iso)

    if not result["ok"]:
        return {
            "ok": False,
            "message": result["message"],
            "total": 0,
            "summary": pd.DataFrame(),
            "fixtures": [],
        }

    fixtures = result["fixtures"]
    grouped = defaultdict(int)

    for item in fixtures:
        league = item.get("league", {}) or {}
        country = league.get("country") or "Sin país"
        league_name = league.get("name") or "Sin liga"
        grouped[(country, league_name)] += 1

    rows = []

    for (country, league_name), matches in grouped.items():
        rows.append({
            "País": country,
            "Liga": league_name,
            "Partidos": matches,
            "Cobertura": _coverage_label(league_name, country),
        })

    summary = pd.DataFrame(rows)

    if not summary.empty:
        summary = summary.sort_values(
            ["País", "Liga"],
            ascending=[True, True],
        ).reset_index(drop=True)

    return {
        "ok": True,
        "message": "Scanner completado.",
        "total": len(fixtures),
        "summary": summary,
        "fixtures": fixtures,
    }
