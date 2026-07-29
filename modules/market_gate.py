from typing import Dict, List, Optional, Tuple
import re

from .market_discovery import APIMarketOption


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _selection_contains(option: APIMarketOption, tokens: List[str]) -> bool:
    text = _clean(option.selection)
    return all(token in text for token in tokens)


def _line_close(a, b, tolerance=0.06) -> bool:
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tolerance


def match_internal_market(
    internal_market: str,
    api_options: List[APIMarketOption],
) -> Optional[APIMarketOption]:
    market = _clean(internal_market)

    def candidates(families):
        return [o for o in api_options if o.family in families]

    # 1X2
    if market == "local 1":
        for o in candidates(["Winner"]):
            if _selection_contains(o, ["home"]) or _clean(o.selection) in ("1", "local"):
                return o
    if market == "empate x":
        for o in candidates(["Winner"]):
            if "draw" in _clean(o.selection) or _clean(o.selection) in ("x", "empate"):
                return o
    if market == "visitante 2":
        for o in candidates(["Winner"]):
            if _selection_contains(o, ["away"]) or _clean(o.selection) in ("2", "visitante"):
                return o

    # Double chance
    if "doble oportunidad 1x" in market:
        for o in candidates(["Winner"]):
            s = _clean(o.selection)
            if "home/draw" in s or "1x" in s or ("home" in s and "draw" in s):
                return o
    if "doble oportunidad x2" in market:
        for o in candidates(["Winner"]):
            s = _clean(o.selection)
            if "draw/away" in s or "x2" in s or ("draw" in s and "away" in s):
                return o
    if "doble oportunidad 12" in market:
        for o in candidates(["Winner"]):
            s = _clean(o.selection)
            if "home/away" in s or "12" == s:
                return o

    # DNB
    if market == "local dnb":
        for o in candidates(["Winner"]):
            s = _clean(o.selection)
            if ("home" in s or s == "1") and "draw no bet" in _clean(o.api_market):
                return o
    if market == "visitante dnb":
        for o in candidates(["Winner"]):
            s = _clean(o.selection)
            if ("away" in s or s == "2") and "draw no bet" in _clean(o.api_market):
                return o

    # BTTS
    if "ambos marcan" in market:
        target_yes = "sí" in market or "si" in market
        for o in candidates(["Goals"]):
            api_name = _clean(o.api_market)
            s = _clean(o.selection)
            if "both teams" in api_name or "ambos" in api_name:
                if target_yes and s in ("yes", "si", "sí"):
                    return o
                if not target_yes and s in ("no",):
                    return o

    # Over/Under total goals
    m = re.search(r"(más|menos) de (\d+\.\d+) goles ft", market)
    if m:
        side = m.group(1)
        line = float(m.group(2))
        for o in candidates(["Goals"]):
            api_name = _clean(o.api_market)
            s = _clean(o.selection)
            if "goal" not in api_name:
                continue
            if not _line_close(o.line, line):
                continue
            if side == "más" and ("over" in s or "más" in s):
                return o
            if side == "menos" and ("under" in s or "menos" in s):
                return o

    # Team goals
    m = re.search(r"(local|visitante) más de (\d+\.\d+) goles", market)
    if m:
        team = m.group(1)
        line = float(m.group(2))
        target_family = "Team Goals"
        for o in candidates([target_family, "Goals"]):
            s = _clean(o.selection)
            api_name = _clean(o.api_market)
            if not _line_close(o.line, line):
                continue
            if "over" not in s and "más" not in s:
                continue
            if team == "local" and ("home" in api_name or "home" in s):
                return o
            if team == "visitante" and ("away" in api_name or "away" in s):
                return o

    # Corners
    m = re.search(r"(más|menos) de (\d+\.\d+) córners", market)
    if m:
        side = m.group(1)
        line = float(m.group(2))
        for o in candidates(["Corners"]):
            if not _line_close(o.line, line):
                continue
            s = _clean(o.selection)
            if side == "más" and ("over" in s or "más" in s):
                return o
            if side == "menos" and ("under" in s or "menos" in s):
                return o

    return None


def attach_api_market(
    market_dict: Dict,
    api_options: List[APIMarketOption],
) -> Optional[Dict]:
    option = match_internal_market(market_dict.get("market", ""), api_options)
    if option is None:
        return None

    probability = float(market_dict.get("probability", 0))
    implicit = 100.0 / option.odd
    edge = probability - implicit

    enriched = dict(market_dict)
    enriched.update({
        "api_market": option.api_market,
        "api_selection": option.selection,
        "bookmaker": option.bookmaker,
        "odd": option.odd,
        "implicit_probability": round(implicit, 2),
        "edge": round(edge, 2),
        "market_available": True,
    })
    return enriched
