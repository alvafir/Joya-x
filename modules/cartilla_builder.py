from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Set


@dataclass
class CartillaPick:
    fixture_id: int
    country: str
    league: str
    match: str
    family: str
    market: str
    api_market: str
    api_selection: str
    bookmaker: str
    odd: float
    implicit_probability: float
    edge: float
    probability: float
    confidence: float
    joya_score: float
    risk: str
    status: str
    reason: str

    def to_dict(self):
        return asdict(self)


def _group(market: str) -> str:
    text = market.lower()
    if "doble oportunidad" in text: return "double_chance"
    if "dnb" in text: return "dnb"
    if "antes del minuto" in text: return "goal_timing"
    if "rango" in text and "goles" in text: return "goal_range"
    if "más de" in text and "goles ft" in text: return "goals_over"
    if "menos de" in text and "goles ft" in text: return "goals_under"
    if "ambos marcan" in text: return "btts"
    if "marca primero" in text: return "first_goal"
    if "córners" in text: return "corners"
    if "tarjetas" in text: return "cards"
    if "tiros" in text or "remates" in text: return "shots"
    return text


def flatten_matches(scanned_matches) -> List[CartillaPick]:
    picks: List[CartillaPick] = []

    for match in scanned_matches:
        if match.status != "APROBADO":
            continue

        for market in match.markets:
            picks.append(CartillaPick(
                fixture_id=match.fixture_id,
                country=match.country,
                league=match.league,
                match=f"{match.home} vs {match.away}",
                family=market.get("family", ""),
                market=market.get("market", ""),
                api_market=market.get("api_market", ""),
                api_selection=market.get("api_selection", ""),
                bookmaker=market.get("bookmaker", ""),
                odd=float(market.get("odd", 0)),
                implicit_probability=float(
                    market.get("implicit_probability", 0)
                ),
                edge=float(market.get("edge", 0)),
                probability=float(market.get("probability", 0)),
                confidence=float(market.get("confidence", 0)),
                joya_score=float(market.get("joya_score", 0)),
                risk=market.get("risk", ""),
                status=market.get("status", ""),
                reason=market.get("reason", ""),
            ))

    return sorted(
        picks,
        key=lambda p: (p.joya_score, p.edge, p.confidence),
        reverse=True,
    )


def diversified_selection(
    picks: List[CartillaPick],
    limit: int,
    min_score: float,
    min_edge: float,
    statuses=("BET", "PRECAUCIÓN"),
    one_per_match: bool = True,
    max_per_group: int = 2,
    allowed_risks=None,
    min_odd: float = 1.01,
    max_odd: float = 20.0,
) -> List[CartillaPick]:
    selected: List[CartillaPick] = []
    used_matches: Set[int] = set()
    group_counts: Dict[str, int] = {}

    for pick in picks:
        if pick.joya_score < min_score:
            continue
        if pick.edge < min_edge:
            continue
        if pick.status not in statuses:
            continue
        if allowed_risks and pick.risk not in allowed_risks:
            continue
        if not (min_odd <= pick.odd <= max_odd):
            continue
        if one_per_match and pick.fixture_id in used_matches:
            continue

        group = _group(pick.market)
        if group_counts.get(group, 0) >= max_per_group:
            continue

        selected.append(pick)
        used_matches.add(pick.fixture_id)
        group_counts[group] = group_counts.get(group, 0) + 1

        if len(selected) >= limit:
            break

    return selected


def build_cartillas(scanned_matches) -> Dict[str, List[CartillaPick]]:
    picks = flatten_matches(scanned_matches)

    return {
        "Top Ranking del Día": diversified_selection(
            picks,
            limit=20,
            min_score=78,
            min_edge=0,
            one_per_match=True,
            max_per_group=3,
        ),
        "Núcleo Sangrado": diversified_selection(
            picks,
            limit=8,
            min_score=86,
            min_edge=2.0,
            statuses=("BET",),
            one_per_match=True,
            max_per_group=1,
            allowed_risks=("Bajo",),
            min_odd=1.10,
            max_odd=2.20,
        ),
        "Elite": diversified_selection(
            picks,
            limit=6,
            min_score=92,
            min_edge=3.0,
            statuses=("BET",),
            one_per_match=True,
            max_per_group=1,
            allowed_risks=("Bajo",),
            min_odd=1.15,
            max_odd=2.10,
        ),
        "Tier S+++": diversified_selection(
            picks,
            limit=8,
            min_score=90,
            min_edge=2.0,
            statuses=("BET",),
            one_per_match=True,
            max_per_group=2,
            max_odd=2.40,
        ),
        "Tier S++": diversified_selection(
            picks,
            limit=10,
            min_score=86,
            min_edge=1.0,
            statuses=("BET", "PRECAUCIÓN"),
            one_per_match=True,
            max_per_group=2,
            max_odd=2.70,
        ),
        "Tier S+": diversified_selection(
            picks,
            limit=12,
            min_score=82,
            min_edge=0.0,
            statuses=("BET", "PRECAUCIÓN"),
            one_per_match=True,
            max_per_group=3,
            max_odd=3.20,
        ),
        "Soñadora": diversified_selection(
            picks,
            limit=7,
            min_score=78,
            min_edge=2.0,
            statuses=("BET", "PRECAUCIÓN"),
            one_per_match=True,
            max_per_group=2,
            min_odd=1.50,
            max_odd=4.50,
        ),
        "Escalera": diversified_selection(
            picks,
            limit=5,
            min_score=84,
            min_edge=1.0,
            statuses=("BET", "PRECAUCIÓN"),
            one_per_match=True,
            max_per_group=1,
            min_odd=1.25,
            max_odd=2.50,
        ),
    }
