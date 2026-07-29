from __future__ import annotations

import pandas as pd


def build_match_table(fixtures: list[dict]) -> pd.DataFrame:
    rows = []

    for item in fixtures or []:
        fixture = item.get("fixture", {}) or {}
        league = item.get("league", {}) or {}
        teams = item.get("teams", {}) or {}

        fixture_id = fixture.get("id")
        home = (teams.get("home") or {}).get("name") or ""
        away = (teams.get("away") or {}).get("name") or ""

        if not fixture_id or not home or not away:
            continue

        rows.append(
            {
                "fixture_id": int(fixture_id),
                "País": league.get("country") or "Sin país",
                "Liga": league.get("name") or "Sin liga",
                "Hora": str(fixture.get("date") or "")[:16].replace("T", " "),
                "Local": home,
                "Visitante": away,
                "Partido": f"{home} vs {away}",
            }
        )

    frame = pd.DataFrame(rows)

    if frame.empty:
        return frame

    return frame.sort_values(
        ["País", "Liga", "Hora", "Partido"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)
