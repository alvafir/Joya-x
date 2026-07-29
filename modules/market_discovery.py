from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional
import re


@dataclass
class APIMarketOption:
    fixture_id: int
    bookmaker_id: Optional[int]
    bookmaker: str
    bet_id: Optional[int]
    api_market: str
    family: str
    normalized_market: str
    selection: str
    line: Optional[float]
    odd: float
    updated_at: Optional[str]

    def to_dict(self):
        return asdict(self)


ALIASES = {
    "match winner": ("Winner", "Ganador 1X2"),
    "home/away": ("Winner", "Ganador sin empate"),
    "double chance": ("Winner", "Doble oportunidad"),
    "draw no bet": ("Winner", "Draw No Bet"),
    "winner first half": ("Winner 1T", "Ganador 1T"),
    "first half winner": ("Winner 1T", "Ganador 1T"),
    "goals over/under": ("Goals", "Total goles FT"),
    "goals over under": ("Goals", "Total goles FT"),
    "goals over/under first half": ("Goals 1T", "Total goles 1T"),
    "both teams score": ("Goals", "Ambos marcan"),
    "both teams to score": ("Goals", "Ambos marcan"),
    "team to score first": ("First Goal", "Equipo marca primero"),
    "first team to score": ("First Goal", "Equipo marca primero"),
    "home team total goals": ("Team Goals", "Goles local"),
    "away team total goals": ("Team Goals", "Goles visitante"),
    "exact goals number": ("Goal Range", "Número exacto de goles"),
    "total corners": ("Corners", "Total córners"),
    "corners over under": ("Corners", "Total córners"),
    "home team total corners": ("Team Corners", "Córners local"),
    "away team total corners": ("Team Corners", "Córners visitante"),
    "total cards": ("Cards", "Total tarjetas"),
    "cards over under": ("Cards", "Total tarjetas"),
    "home team total cards": ("Team Cards", "Tarjetas local"),
    "away team total cards": ("Team Cards", "Tarjetas visitante"),
}


def _clean(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).lower()


def normalize_market_name(api_market: str) -> tuple[str, str]:
    cleaned = _clean(api_market)
    for key, value in ALIASES.items():
        if key in cleaned:
            return value

    if "corner" in cleaned:
        return "Corners", api_market
    if "card" in cleaned or "booking" in cleaned:
        return "Cards", api_market
    if "shot" in cleaned or "attempt" in cleaned:
        return "Shots", api_market
    if "goal" in cleaned or "score" in cleaned:
        return "Goals", api_market
    if "winner" in cleaned or "chance" in cleaned:
        return "Winner", api_market

    return "Other", api_market


def parse_line(selection: Any) -> Optional[float]:
    text = str(selection or "")
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    if not matches:
        return None
    try:
        return float(matches[-1])
    except ValueError:
        return None


def _safe_odd(value: Any) -> Optional[float]:
    try:
        odd = float(value)
        return odd if odd > 1.0 else None
    except (TypeError, ValueError):
        return None


def discover_markets(
    fixture_id: int,
    odds_payload: Dict[str, Any],
) -> List[APIMarketOption]:
    output: List[APIMarketOption] = []

    for response_row in odds_payload.get("response") or []:
        update = response_row.get("update")
        bookmakers = response_row.get("bookmakers") or []

        for bookmaker in bookmakers:
            bookmaker_id = bookmaker.get("id")
            bookmaker_name = bookmaker.get("name") or "Bookmaker"
            bets = bookmaker.get("bets") or []

            for bet in bets:
                bet_id = bet.get("id")
                api_market = bet.get("name") or "Mercado"
                family, normalized = normalize_market_name(api_market)

                for value in bet.get("values") or []:
                    selection = value.get("value") or ""
                    odd = _safe_odd(value.get("odd"))
                    if odd is None:
                        continue

                    output.append(APIMarketOption(
                        fixture_id=fixture_id,
                        bookmaker_id=bookmaker_id,
                        bookmaker=bookmaker_name,
                        bet_id=bet_id,
                        api_market=api_market,
                        family=family,
                        normalized_market=normalized,
                        selection=str(selection),
                        line=parse_line(selection),
                        odd=round(odd, 3),
                        updated_at=update,
                    ))

    return output


def best_price(options: Iterable[APIMarketOption]) -> List[APIMarketOption]:
    best: Dict[tuple, APIMarketOption] = {}

    for option in options:
        key = (
            option.fixture_id,
            option.family,
            option.normalized_market,
            option.selection,
        )
        current = best.get(key)
        if current is None or option.odd > current.odd:
            best[key] = option

    return sorted(
        best.values(),
        key=lambda item: (
            item.family,
            item.normalized_market,
            item.selection,
        ),
    )
