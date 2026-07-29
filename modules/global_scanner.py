from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from .cache import (
    cached_prediction,
    cached_recent_team,
    cached_h2h_safe,
    cached_odds_by_fixture_safe,
)
from .data_quality import evaluate_data_quality
from .projection import build_projection_v2
from .projection_v3 import build_projection_v3
from .intelligence_hub import build_intelligence_report
from .market_orchestrator import evaluate_all, global_ranking
from .market_discovery import discover_markets, best_price
from .market_gate import attach_api_market


@dataclass
class ScannedMatch:
    fixture_id: int
    country: str
    league: str
    home: str
    away: str
    league_score: float
    status: str
    reason: str
    api_market_count: int
    markets: List[Dict[str, Any]]
    discarded: List[Dict[str, Any]]

    def to_dict(self):
        return asdict(self)


def league_score_for_row(row: Dict[str, Any]) -> float:
    score = 80.0
    league = str(row.get("liga") or "").lower()
    country = str(row.get("país") or "").lower()

    if any(x in league for x in ("friendly", "amistoso")):
        score = 60.0
    if any(x in league for x in (
        "u17", "u18", "u19", "u20", "u21",
        "youth", "reserve", "reserves"
    )):
        score = min(score, 55.0)
    if any(x in league for x in ("women", "femenina")):
        score = min(score, 76.0)
    if country in ("world", ""):
        score = min(score, 78.0)

    return score


def _empty(base, status, reason):
    return ScannedMatch(
        **base,
        status=status,
        reason=reason,
        api_market_count=0,
        markets=[],
        discarded=[],
    )


def analyze_fixture(
    api_key: str,
    row: Dict[str, Any],
    min_league_score: float = 70.0,
    bookmaker_id=None,
    min_edge: float = 0.0,
) -> ScannedMatch:
    raw = row.get("raw") or {}
    teams = raw.get("teams") or {}
    home_info = teams.get("home") or {}
    away_info = teams.get("away") or {}

    fixture_id = int(row.get("fixture_id"))
    home_id = home_info.get("id")
    away_id = away_info.get("id")
    league_score = league_score_for_row(row)

    base = dict(
        fixture_id=fixture_id,
        country=row.get("país") or "",
        league=row.get("liga") or "",
        home=row.get("local") or "",
        away=row.get("visitante") or "",
        league_score=league_score,
    )

    if league_score < min_league_score:
        return _empty(base, "NO BET", "League Score bajo el filtro.")

    if not home_id or not away_id:
        return _empty(base, "NO BET", "Faltan IDs de equipos.")

    try:
        odds_result = cached_odds_by_fixture_safe(
            api_key,
            fixture_id,
            bookmaker_id,
        )
        api_options = best_price(
            discover_markets(
                fixture_id,
                odds_result.get("payload") or {"response": []},
            )
        )

        if not api_options:
            return _empty(
                base,
                "NO BET",
                "API-Football no entregó mercados/cuotas para este partido.",
            )

        prediction = cached_prediction(api_key, fixture_id)
        home_recent = cached_recent_team(api_key, int(home_id), 20)
        away_recent = cached_recent_team(api_key, int(away_id), 20)
        h2h_result = cached_h2h_safe(api_key, int(home_id), int(away_id), 10)
        h2h_payload = h2h_result.get("payload") or {"response": []}

        quality = evaluate_data_quality(raw, prediction, league_score)
        if not quality.approved:
            result = _empty(
                base,
                "NO BET",
                f"Data Quality no aprobada ({quality.score:.0f}/100).",
            )
            result.api_market_count = len(api_options)
            return result

        projection = build_projection_v2(
            prediction,
            home_recent,
            away_recent,
            h2h_payload,
            int(home_id),
            int(away_id),
            quality.score,
        )
        intelligence = build_intelligence_report(
            home_recent,
            away_recent,
            int(home_id),
            int(away_id),
            league_score,
        )
        projection_v3 = build_projection_v3(projection, intelligence)
        projection = projection_v3.base

        engines = evaluate_all(
            projection,
            quality,
            league_score,
            corner_projection=None,
            h2h_report=None,
        )
        ranking = global_ranking(engines, 30)

        approved = []
        discarded = []

        for market in ranking:
            raw_market = market.to_dict()
            enriched = attach_api_market(raw_market, api_options)

            if enriched is None:
                discarded.append({
                    **raw_market,
                    "discard_reason": "Mercado no disponible en API-Football.",
                })
                continue

            if enriched["edge"] < min_edge:
                discarded.append({
                    **enriched,
                    "discard_reason": (
                        f"Edge insuficiente ({enriched['edge']:.2f}%)."
                    ),
                })
                continue

            if market.status not in ("BET", "PRECAUCIÓN"):
                discarded.append({
                    **enriched,
                    "discard_reason": f"Estado {market.status}.",
                })
                continue

            approved.append(enriched)

        if not approved:
            return ScannedMatch(
                **base,
                status="NO BET",
                reason="No hubo mercados disponibles con valor suficiente.",
                api_market_count=len(api_options),
                markets=[],
                discarded=discarded,
            )

        approved.sort(
            key=lambda item: (
                item.get("joya_score", 0),
                item.get("edge", 0),
            ),
            reverse=True,
        )

        return ScannedMatch(
            **base,
            status="APROBADO",
            reason=f"{len(approved)} mercados disponibles y validados.",
            api_market_count=len(api_options),
            markets=approved,
            discarded=discarded,
        )

    except Exception as exc:
        return ScannedMatch(
            **base,
            status="ERROR",
            reason=str(exc),
            api_market_count=0,
            markets=[],
            discarded=[],
        )


def scan_day(
    api_key: str,
    rows: List[Dict[str, Any]],
    max_matches: int = 30,
    min_league_score: float = 70.0,
    bookmaker_id=None,
    min_edge: float = 0.0,
    progress_callback=None,
) -> List[ScannedMatch]:
    eligible = [
        row for row in rows
        if league_score_for_row(row) >= min_league_score
    ]
    selected = sorted(
        eligible,
        key=league_score_for_row,
        reverse=True,
    )[:max_matches]

    output: List[ScannedMatch] = []
    total = len(selected)

    for index, row in enumerate(selected, start=1):
        result = analyze_fixture(
            api_key,
            row,
            min_league_score=min_league_score,
            bookmaker_id=bookmaker_id,
            min_edge=min_edge,
        )
        output.append(result)

        if progress_callback:
            progress_callback(index, total, result)

    return output
