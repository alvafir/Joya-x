from typing import Any, Dict, List
import pandas as pd

def fixtures_to_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for item in payload.get("response") or []:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        teams = item.get("teams") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        rows.append({
            "fixture_id": fixture.get("id"),
            "hora": fixture.get("date"),
            "país": league.get("country"),
            "liga": league.get("name"),
            "temporada": league.get("season"),
            "local": home.get("name"),
            "visitante": away.get("name"),
            "partido": f"{home.get('name', '?')} vs {away.get('name', '?')}",
            "raw": item,
        })
    return rows

def fixtures_dataframe(payload: Dict[str, Any]) -> pd.DataFrame:
    rows = fixtures_to_rows(payload)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).drop(columns=["raw"])
