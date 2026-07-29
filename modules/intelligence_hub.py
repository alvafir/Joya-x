from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from .utils import safe_float, clamp


@dataclass
class TeamWindow:
    sample: int
    goals_for: float
    goals_against: float
    win_rate: float
    draw_rate: float
    loss_rate: float
    clean_sheet_rate: float
    scored_rate: float

    def to_dict(self):
        return asdict(self)


@dataclass
class IntelligenceReport:
    home_5: TeamWindow
    home_10: TeamWindow
    home_20: TeamWindow
    away_5: TeamWindow
    away_10: TeamWindow
    away_20: TeamWindow
    home_split: Dict[str, float]
    away_split: Dict[str, float]
    league_score: float
    volatility: float
    coverage: float
    warnings: List[str]

    def to_dict(self):
        return {
            "home_5": self.home_5.to_dict(),
            "home_10": self.home_10.to_dict(),
            "home_20": self.home_20.to_dict(),
            "away_5": self.away_5.to_dict(),
            "away_10": self.away_10.to_dict(),
            "away_20": self.away_20.to_dict(),
            "home_split": self.home_split,
            "away_split": self.away_split,
            "league_score": self.league_score,
            "volatility": self.volatility,
            "coverage": self.coverage,
            "warnings": self.warnings,
        }


def _completed(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for row in payload.get("response") or []:
        goals = row.get("goals") or {}
        if safe_float(goals.get("home")) is None or safe_float(goals.get("away")) is None:
            continue
        out.append(row)
    return out


def _window(payload: Dict[str, Any], team_id: int, n: int) -> TeamWindow:
    rows = _completed(payload)[:n]
    gf = ga = wins = draws = losses = clean = scored = 0
    used = 0

    for row in rows:
        teams = row.get("teams") or {}
        goals = row.get("goals") or {}
        hid = (teams.get("home") or {}).get("id")
        aid = (teams.get("away") or {}).get("id")
        gh = float(goals.get("home"))
        ga_ = float(goals.get("away"))

        if team_id == hid:
            team_gf, team_ga = gh, ga_
        elif team_id == aid:
            team_gf, team_ga = ga_, gh
        else:
            continue

        used += 1
        gf += team_gf
        ga += team_ga
        clean += int(team_ga == 0)
        scored += int(team_gf > 0)
        if team_gf > team_ga:
            wins += 1
        elif team_gf == team_ga:
            draws += 1
        else:
            losses += 1

    if used == 0:
        return TeamWindow(0, 0, 0, 0, 0, 0, 0, 0)

    return TeamWindow(
        sample=used,
        goals_for=round(gf / used, 2),
        goals_against=round(ga / used, 2),
        win_rate=round(wins / used * 100, 1),
        draw_rate=round(draws / used * 100, 1),
        loss_rate=round(losses / used * 100, 1),
        clean_sheet_rate=round(clean / used * 100, 1),
        scored_rate=round(scored / used * 100, 1),
    )


def _split(payload: Dict[str, Any], team_id: int, venue: str) -> Dict[str, float]:
    rows = _completed(payload)
    gf = ga = n = 0
    for row in rows:
        teams = row.get("teams") or {}
        goals = row.get("goals") or {}
        hid = (teams.get("home") or {}).get("id")
        aid = (teams.get("away") or {}).get("id")
        gh = float(goals.get("home"))
        ga_ = float(goals.get("away"))

        if venue == "home" and team_id == hid:
            gf += gh; ga += ga_; n += 1
        elif venue == "away" and team_id == aid:
            gf += ga_; ga += gh; n += 1

    return {
        "sample": n,
        "goals_for": round(gf / n, 2) if n else 0.0,
        "goals_against": round(ga / n, 2) if n else 0.0,
    }


def build_intelligence_report(
    home_payload: Dict[str, Any],
    away_payload: Dict[str, Any],
    home_team_id: int,
    away_team_id: int,
    league_score: float,
) -> IntelligenceReport:
    warnings: List[str] = []

    h5 = _window(home_payload, home_team_id, 5)
    h10 = _window(home_payload, home_team_id, 10)
    h20 = _window(home_payload, home_team_id, 20)
    a5 = _window(away_payload, away_team_id, 5)
    a10 = _window(away_payload, away_team_id, 10)
    a20 = _window(away_payload, away_team_id, 20)

    hs = _split(home_payload, home_team_id, "home")
    avs = _split(away_payload, away_team_id, "away")

    total_sample = h20.sample + a20.sample
    coverage = clamp(total_sample / 40 * 100)

    # Volatilidad simple basada en diferencias entre ventanas 5 y 10.
    volatility = clamp(
        abs(h5.goals_for - h10.goals_for) * 18
        + abs(h5.goals_against - h10.goals_against) * 14
        + abs(a5.goals_for - a10.goals_for) * 18
        + abs(a5.goals_against - a10.goals_against) * 14
    )

    if h10.sample < 5:
        warnings.append("Muestra local reciente reducida.")
    if a10.sample < 5:
        warnings.append("Muestra visitante reciente reducida.")
    if hs["sample"] < 3:
        warnings.append("Poca muestra del local actuando en casa.")
    if avs["sample"] < 3:
        warnings.append("Poca muestra del visitante actuando fuera.")

    return IntelligenceReport(
        home_5=h5,
        home_10=h10,
        home_20=h20,
        away_5=a5,
        away_10=a10,
        away_20=a20,
        home_split=hs,
        away_split=avs,
        league_score=round(league_score, 1),
        volatility=round(volatility, 1),
        coverage=round(coverage, 1),
        warnings=warnings,
    )
