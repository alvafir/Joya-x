import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "joya_learning.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            league TEXT,
            home_team TEXT,
            away_team TEXT,
            expected_home REAL,
            expected_away REAL,
            expected_total REAL,
            uncertainty REAL,
            stability REAL,
            payload TEXT,
            UNIQUE(fixture_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS market_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER NOT NULL,
            family TEXT,
            market TEXT,
            probability REAL,
            confidence REAL,
            joya_score REAL,
            status TEXT,
            won INTEGER,
            UNIQUE(fixture_id, market)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            fixture_id INTEGER PRIMARY KEY,
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            home_goals INTEGER,
            away_goals INTEGER,
            notes TEXT
        )
        """)


def save_analysis(
    fixture: Dict[str, Any],
    projection: Dict[str, Any],
    markets: List[Dict[str, Any]],
):
    initialize()
    base = projection["base"]
    with connect() as conn:
        conn.execute("""
        INSERT INTO analyses (
            fixture_id, league, home_team, away_team,
            expected_home, expected_away, expected_total,
            uncertainty, stability, payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fixture_id) DO UPDATE SET
            league=excluded.league,
            home_team=excluded.home_team,
            away_team=excluded.away_team,
            expected_home=excluded.expected_home,
            expected_away=excluded.expected_away,
            expected_total=excluded.expected_total,
            uncertainty=excluded.uncertainty,
            stability=excluded.stability,
            payload=excluded.payload
        """, (
            fixture["id"], fixture.get("league"), fixture.get("home"), fixture.get("away"),
            base["home_expected_goals"], base["away_expected_goals"],
            base["expected_goals"], projection["uncertainty"], projection["stability"],
            json.dumps(projection, ensure_ascii=False),
        ))

        for market in markets:
            conn.execute("""
            INSERT INTO market_predictions (
                fixture_id, family, market, probability,
                confidence, joya_score, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fixture_id, market) DO UPDATE SET
                family=excluded.family,
                probability=excluded.probability,
                confidence=excluded.confidence,
                joya_score=excluded.joya_score,
                status=excluded.status
            """, (
                fixture["id"], market["family"], market["market"],
                market["probability"], market["confidence"],
                market["joya_score"], market["status"],
            ))


def _settle_market(market: str, home_goals: int, away_goals: int) -> Optional[int]:
    total = home_goals + away_goals
    text = market.lower()

    if text == "local 1": return int(home_goals > away_goals)
    if text == "empate x": return int(home_goals == away_goals)
    if text == "visitante 2": return int(away_goals > home_goals)
    if "doble oportunidad 1x" in text: return int(home_goals >= away_goals)
    if "doble oportunidad x2" in text: return int(away_goals >= home_goals)
    if "doble oportunidad 12" in text: return int(home_goals != away_goals)
    if "ambos marcan — sí" in text: return int(home_goals > 0 and away_goals > 0)
    if "ambos marcan — no" in text: return int(home_goals == 0 or away_goals == 0)
    if "local más de 0.5 goles" in text: return int(home_goals >= 1)
    if "visitante más de 0.5 goles" in text: return int(away_goals >= 1)
    if "local más de 1.5 goles" in text: return int(home_goals >= 2)
    if "visitante más de 1.5 goles" in text: return int(away_goals >= 2)

    if "goles ft" in text:
        import re
        m = re.search(r"(más|menos) de (\d+\.\d+)", text)
        if m:
            side, line = m.group(1), float(m.group(2))
            return int(total > line) if side == "más" else int(total < line)

    if "rango 1-5 goles" in text: return int(1 <= total <= 5)
    if "rango 1-4 goles" in text: return int(1 <= total <= 4)
    if "rango 2-5 goles" in text: return int(2 <= total <= 5)
    if "rango 2-4 goles" in text: return int(2 <= total <= 4)

    return None


def record_result(fixture_id: int, home_goals: int, away_goals: int, notes: str = ""):
    initialize()
    with connect() as conn:
        conn.execute("""
        INSERT INTO results (fixture_id, home_goals, away_goals, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(fixture_id) DO UPDATE SET
            home_goals=excluded.home_goals,
            away_goals=excluded.away_goals,
            notes=excluded.notes
        """, (fixture_id, home_goals, away_goals, notes))

        rows = conn.execute(
            "SELECT id, market FROM market_predictions WHERE fixture_id=?",
            (fixture_id,)
        ).fetchall()

        for row in rows:
            won = _settle_market(row["market"], home_goals, away_goals)
            if won is not None:
                conn.execute(
                    "UPDATE market_predictions SET won=? WHERE id=?",
                    (won, row["id"])
                )


def summary_metrics() -> Dict[str, Any]:
    initialize()
    with connect() as conn:
        overall = conn.execute("""
            SELECT
                COUNT(*) AS settled,
                SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) AS wins
            FROM market_predictions
            WHERE won IS NOT NULL
        """).fetchone()

        by_family = conn.execute("""
            SELECT family,
                   COUNT(*) AS settled,
                   SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) AS wins
            FROM market_predictions
            WHERE won IS NOT NULL
            GROUP BY family
            ORDER BY settled DESC
        """).fetchall()

        projections = conn.execute("""
            SELECT a.expected_total, r.home_goals + r.away_goals AS actual_total
            FROM analyses a
            JOIN results r ON r.fixture_id = a.fixture_id
        """).fetchall()

    settled = overall["settled"] or 0
    wins = overall["wins"] or 0
    accuracy = wins / settled * 100 if settled else 0.0

    mae = 0.0
    if projections:
        mae = sum(abs(r["expected_total"] - r["actual_total"]) for r in projections) / len(projections)

    return {
        "settled": settled,
        "wins": wins,
        "accuracy": round(accuracy, 1),
        "goal_mae": round(mae, 2),
        "by_family": [dict(r) for r in by_family],
    }


def recent_analyses(limit: int = 30) -> List[Dict[str, Any]]:
    initialize()
    with connect() as conn:
        rows = conn.execute("""
            SELECT a.*, r.home_goals, r.away_goals
            FROM analyses a
            LEFT JOIN results r ON r.fixture_id = a.fixture_id
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]
