# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastapi>=0.111",
#   "uvicorn>=0.29",
# ]
# ///
"""
baz_server.py — Baz local context server.

Runs on localhost:8765 ONLY. Never exposed to the internet.
BetMate's /api/chat route fetches from here before calling Anthropic API.
The model IP (ELO weights, tier config, raw signals) never leaves this machine.
Only plain-English summaries travel online.

Start:
    & C:\\Users\\ElliotBladen\\Apps\\BettingEngine\\.venv\\Scripts\\python.exe baz_server.py

Or via uv:
    & C:\\Users\\ElliotBladen\\.local\\bin\\uv.exe run python baz_server.py
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
BETMATE_ROOT = Path(os.environ.get("BETMATE_ROOT", str(BASE_DIR.parent)))
DB_PATH = BASE_DIR / "data" / "model.db"
RESULTS_DIR = BASE_DIR / "results"
BETS_CSV = BASE_DIR / "data" / "bets" / "actual_bets_2026.csv"
CONFLUENCE_JSON     = BASE_DIR / "outputs" / "nrl_t9_confluence_latest.json"
AFL_CONFLUENCE_JSON = BASE_DIR / "outputs" / "afl_t9_confluence_latest.json"
AFL_INJURIES_JSON   = BETMATE_ROOT / "data" / "afl" / "injuries" / "processed" / "latest-injuries.json"

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Baz Context Server", version="1.0.0")

# Only allow requests from the local Next.js dev/prod server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── DB helpers ─────────────────────────────────────────────────────────────────
def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def _one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


# ── Pricing CSV helpers ────────────────────────────────────────────────────────
def _latest_pricing_csv() -> Path | None:
    """Most recent NRL pricing CSV."""
    candidates = sorted(
        [f for f in RESULTS_DIR.glob("r*_*pricing*_2026.csv")]
        + [f for f in RESULTS_DIR.glob("r*_pricing_2026.csv")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _latest_afl_pricing_csv() -> Path | None:
    """Most recent AFL pricing CSV (r*_afl_*2026.csv)."""
    candidates = sorted(
        RESULTS_DIR.glob("r*_afl_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _read_pricing_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="cp1252", errors="replace") as f:
        return list(csv.DictReader(f))


def _ev_pct(model_odds: float, market_odds: float) -> float:
    """EV as a percentage. Positive = value."""
    if model_odds <= 0 or market_odds <= 0:
        return 0.0
    model_prob = 1.0 / model_odds
    return round((model_prob * market_odds - 1) * 100, 1)


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _read_latest_baz_status() -> dict:
    path = BASE_DIR / "outputs" / "baz" / "latest_status.json"
    if not path.exists():
        return {
            "readiness": "unknown",
            "blockers": ["outputs/baz/latest_status.json has not been generated"],
            "next_actions": ["python scripts/baz_status.py"],
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not read Baz status: {exc}") from exc


def _norm_query(value: str) -> str:
    return " ".join(str(value or "").lower().replace(".", "").replace("-", " ").split())


# ── Confluence helpers ─────────────────────────────────────────────────────────
def _load_confluence(path: Path = CONFLUENCE_JSON) -> dict[str, dict]:
    """Load T9 matrix confluence. Returns {home_team_lower: confluence_flags}."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {g["home"].lower(): g.get("confluence", {}) for g in data.get("games", [])}
    except Exception:
        return {}


# ── AFL injury helpers ─────────────────────────────────────────────────────────
def _load_afl_injuries() -> dict[str, list[dict]]:
    """Load AFL injuries grouped by team name."""
    if not AFL_INJURIES_JSON.exists():
        return {}
    try:
        data = json.loads(AFL_INJURIES_JSON.read_text(encoding="utf-8"))
        by_team: dict[str, list[dict]] = {}
        for item in data:
            team = item.get("team", "")
            if not team:
                continue
            by_team.setdefault(team, []).append({
                "player": item.get("player", ""),
                "status": item.get("status", ""),
                "notes": item.get("notes", ""),
            })
        return by_team
    except Exception:
        return {}


def _team_injury_str(injuries_by_team: dict[str, list[dict]], team: str) -> str:
    """Return a compact comma-separated injury string for a team."""
    players = injuries_by_team.get(team) or next(
        (v for k, v in injuries_by_team.items()
         if team.lower() in k.lower() or k.lower() in team.lower()),
        [],
    )
    parts = [
        f"{p['player']} ({p['status']})"
        for p in players
        if p.get("status") in ("out", "doubtful")
    ]
    return ", ".join(parts[:8])


# ── CLV helpers ────────────────────────────────────────────────────────────────
def _clv_summary(n_weeks: int = 4) -> dict:
    """Read actual_bets_2026.csv and compute last-N-rounds CLV snapshot."""
    if not BETS_CSV.exists():
        return {}
    bets: list[dict] = []
    with open(BETS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("pnl") and row.get("result") in ("win", "loss"):
                bets.append(row)

    if not bets:
        return {}

    # Sort by round desc, take last N rounds
    rounds = sorted({int(r["round"]) for r in bets if r.get("round")}, reverse=True)[:n_weeks]
    recent = [r for r in bets if int(r.get("round", 0)) in rounds]

    total_pnl = sum(_safe_float(r["pnl"]) for r in recent)
    total_staked = sum(_safe_float(r["stake"]) for r in recent)
    wins = sum(1 for r in recent if r["result"] == "win")
    roi = round(total_pnl / total_staked * 100, 1) if total_staked else 0.0
    win_rate = round(wins / len(recent), 2) if recent else 0.0

    return {
        "rounds_covered": sorted(rounds, reverse=True),
        "bets": len(recent),
        "profit": round(total_pnl, 2),
        "roi_pct": roi,
        "win_rate": win_rate,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "generated_at": datetime.now(timezone.utc).isoformat()}


@app.get("/status")
def status() -> dict:
    """Return the latest structured Baz readiness report."""
    return _read_latest_baz_status()


@app.get("/db/signals")
def db_signals(
    sport: str = Query(default="NRL"),
    season: int = Query(default=2026),
    round: int | None = Query(default=None),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> dict:
    """Return canonical DB-backed Baz signals from the pricing pipeline."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not found")

    conn = _db()
    round_number = round
    if round_number is None:
        row = conn.execute(
            """
            select max(round_number) as round_number
            from matches
            where sport = ? and season = ?
            """,
            (sport.upper(), season),
        ).fetchone()
        round_number = int(row["round_number"]) if row and row["round_number"] is not None else None

    params: list[Any] = [sport.upper(), season]
    where = "m.sport = ? and m.season = ?"
    if round_number is not None:
        where += " and m.round_number = ?"
        params.append(round_number)

    rows = _rows(
        conn,
        f"""
        select
            m.match_id,
            m.round_number,
            m.match_date,
            h.team_name as home_team,
            a.team_name as away_team,
            s.market_type,
            s.selection_name,
            s.line_value,
            s.market_odds,
            s.model_odds,
            s.model_probability,
            s.ev_percent,
            s.confidence_level,
            s.signal_label,
            s.veto_flag,
            s.veto_reason,
            b.bookmaker_code,
            b.bookmaker_name
        from signals s
        join matches m on m.match_id = s.match_id
        join teams h on h.team_id = m.home_team_id
        join teams a on a.team_id = m.away_team_id
        join bookmakers b on b.bookmaker_id = s.bookmaker_id
        where {where}
        order by m.match_date, m.match_id, s.ev_percent desc
        """,
        tuple(params),
    )
    conn.close()

    if home:
        home_q = _norm_query(home)
        rows = [row for row in rows if home_q in _norm_query(row["home_team"]) or home_q in _norm_query(row["away_team"])]
    if away:
        away_q = _norm_query(away)
        rows = [row for row in rows if away_q in _norm_query(row["home_team"]) or away_q in _norm_query(row["away_team"])]

    label_counts: dict[str, int] = {}
    for row in rows:
        label = str(row["signal_label"])
        label_counts[label] = label_counts.get(label, 0) + 1

    watch = [row for row in rows if row["signal_label"] == "watch"]
    recommendations = [
        row for row in rows
        if row["signal_label"] in {"recommend_small", "recommend_medium", "recommend_strong"}
    ]
    actionable = recommendations or watch

    return {
        "sport": sport.upper(),
        "season": season,
        "round": round_number,
        "counts": {
            "signals": len(rows),
            "by_label": label_counts,
        },
        "recommendations": recommendations,
        "watch": watch,
        "actionable": actionable,
        "signals": rows,
    }


def _context_nrl() -> dict:
    pricing_csv = _latest_pricing_csv()
    if not pricing_csv:
        raise HTTPException(status_code=503, detail="No NRL pricing file found")

    rows = _read_pricing_csv(pricing_csv)
    if not rows:
        raise HTTPException(status_code=503, detail="NRL pricing file is empty")

    season = rows[0].get("season", "?")
    round_num = rows[0].get("round", "?")
    signals: list[dict] = []
    games: list[dict] = []
    confluence_map = _load_confluence(CONFLUENCE_JSON)

    for row in rows:
        home = row.get("home_team", "")
        away = row.get("away_team", "")
        fair_home = _safe_float(row.get("fair_home_odds"), 0)
        fair_away = _safe_float(row.get("fair_away_odds"), 0)
        mkt_home = _safe_float(row.get("h2h_home_105"), 0)
        mkt_away = _safe_float(row.get("h2h_away_105"), 0)
        home_ev = _ev_pct(fair_home, mkt_home) if fair_home and mkt_home else 0.0
        away_ev = _ev_pct(fair_away, mkt_away) if fair_away and mkt_away else 0.0
        referee = row.get("referee", "") or "TBC"
        ref_bucket = row.get("ref_bucket", "neutral")
        injuries_home = row.get("home_outs", "")
        injuries_away = row.get("away_outs", "")
        weather = row.get("weather_condition", "")
        temp = _safe_float(row.get("temp_c"), 0)
        wind = _safe_float(row.get("wind_kmh"), 0)
        fair_hcap = _safe_float(row.get("fair_hcap_line"), 0)
        fair_total = _safe_float(row.get("fair_total_line"), 0)

        game_summary = {
            "home": home, "away": away,
            "date": row.get("date", ""), "kickoff": row.get("kickoff", ""),
            "venue": row.get("venue", ""),
            "model_h2h": {"home": fair_home, "away": fair_away},
            "market_h2h": {"home": mkt_home, "away": mkt_away},
            "model_hcap": fair_hcap, "model_total": fair_total,
            "ev": {"home_h2h": home_ev, "away_h2h": away_ev},
            "referee": referee, "ref_bucket": ref_bucket,
            "injuries": {"home": injuries_home, "away": injuries_away},
            "weather": {"condition": weather, "temp_c": temp, "wind_kmh": wind},
            "explanation": row.get("explanation", ""),
            "confluence": confluence_map.get(home.lower(), {}),
        }
        games.append(game_summary)

        flags: list[str] = []
        if injuries_home:
            flags.append(f"{home} outs: {injuries_home[:80]}")
        if injuries_away:
            flags.append(f"{away} outs: {injuries_away[:80]}")
        if ref_bucket not in ("neutral", ""):
            flags.append(f"{referee} ({ref_bucket})")
        if home_ev >= 20.0:
            signals.append({"selection": home, "opponent": away, "market": "H2H",
                            "model_odds": fair_home, "market_odds": mkt_home,
                            "ev_pct": home_ev, "flags": flags})
        if away_ev >= 20.0:
            signals.append({"selection": away, "opponent": home, "market": "H2H",
                            "model_odds": fair_away, "market_odds": mkt_away,
                            "ev_pct": away_ev, "flags": flags})

    clv = _clv_summary()
    return {
        "season": season, "round": round_num, "sport": "NRL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pricing_file": pricing_csv.name,
        "signals": signals, "games": games, "clv_last_4_rounds": clv,
        "model_summary": (
            f"{len(signals)} H2H signal(s) above 20% EV threshold this round. "
            "Handicap and totals signals may still exist — compare model_hcap/model_total in per-game context to live market lines."
            if signals else
            "No H2H signals above 20% EV threshold this round. "
            "Handicap and totals value may still exist — compare model_hcap/model_total in per-game context to live market lines."
        ),
    }


def _context_afl() -> dict:
    pricing_csv = _latest_afl_pricing_csv()
    if not pricing_csv:
        raise HTTPException(status_code=503, detail="No AFL pricing file found")

    rows = _read_pricing_csv(pricing_csv)
    if not rows:
        raise HTTPException(status_code=503, detail="AFL pricing file is empty")

    season = rows[0].get("season", "?")
    round_num = rows[0].get("round_number", "?")
    games: list[dict] = []
    confluence_map = _load_confluence(AFL_CONFLUENCE_JSON)
    afl_injuries = _load_afl_injuries()

    for row in rows:
        home = row.get("home_team", "")
        away = row.get("away_team", "")
        rules_home = _safe_float(row.get("rules_home_odds"), 0)
        rules_away = _safe_float(row.get("rules_away_odds"), 0)
        rules_margin = _safe_float(row.get("rules_margin"), 0)   # home perspective
        rules_total = _safe_float(row.get("rules_total"), 0)
        ml_margin = _safe_float(row.get("ml_margin"), 0)
        ml_total = _safe_float(row.get("ml_total"), 0)
        ml_prob = _safe_float(row.get("ml_h2h"), 0)
        ml_home_odds = round(1 / ml_prob, 2) if ml_prob > 0.01 else 0
        ml_away_odds = round(1 / (1 - ml_prob), 2) if 0.01 < ml_prob < 0.99 else 0
        injuries_home = _team_injury_str(afl_injuries, home)
        injuries_away = _team_injury_str(afl_injuries, away)

        game_summary = {
            "home": home, "away": away,
            "date": row.get("game_date", ""), "kickoff": "",
            "venue": row.get("venue", ""),
            "model_h2h": {"home": rules_home, "away": rules_away},
            "market_h2h": {"home": 0, "away": 0},
            "model_hcap": rules_margin, "model_total": rules_total,
            "ml_model": {"margin": ml_margin, "total": ml_total,
                         "home_odds": ml_home_odds, "away_odds": ml_away_odds},
            "ev": {"home_h2h": 0, "away_h2h": 0},
            "referee": "N/A", "ref_bucket": "",
            "injuries": {"home": injuries_home, "away": injuries_away},
            "weather": {"condition": "", "temp_c": 0, "wind_kmh": 0},
            "explanation": "",
            "confluence": confluence_map.get(home.lower(), {}),
        }
        games.append(game_summary)

    return {
        "season": season, "round": round_num, "sport": "AFL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pricing_file": pricing_csv.name,
        "signals": [], "games": games, "clv_last_4_rounds": {},
        "model_summary": (
            "AFL model: rules-based ELO + ML shadow. "
            "No EV threshold — use model_hcap vs live market and matrix signals for value. "
            "ML model generally more conservative than rules on home team margins."
        ),
    }


@app.get("/context/round")
def context_round(sport: str = Query(default="NRL")) -> dict:
    """Return context summary for the current round. sport=NRL|AFL."""
    if sport.upper() == "AFL":
        return _context_afl()
    return _context_nrl()


def _find_game_row(rows: list[dict], home: str, away: str) -> dict | None:
    home_lower = home.lower()
    away_lower = away.lower()
    return next(
        (r for r in rows
         if home_lower in r.get("home_team", "").lower()
         or away_lower in r.get("away_team", "").lower()
         or home_lower in r.get("away_team", "").lower()
         or away_lower in r.get("home_team", "").lower()),
        None,
    )


@app.get("/context/game")
def context_game(
    home: str = Query(..., description="Home team name"),
    away: str = Query(..., description="Away team name"),
    sport: str = Query(default="NRL"),
) -> dict:
    """Return focused context for a specific game. sport=NRL|AFL."""
    if sport.upper() == "AFL":
        return _context_game_afl(home, away)
    return _context_game_nrl(home, away)


def _context_game_nrl(home: str, away: str) -> dict:
    pricing_csv = _latest_pricing_csv()
    if not pricing_csv:
        raise HTTPException(status_code=503, detail="No NRL pricing file found")

    rows = _read_pricing_csv(pricing_csv)
    match = _find_game_row(rows, home, away)
    if not match:
        raise HTTPException(status_code=404, detail=f"Game not found: {home} vs {away}")

    fair_home = _safe_float(match.get("fair_home_odds"), 0)
    fair_away = _safe_float(match.get("fair_away_odds"), 0)
    mkt_home = _safe_float(match.get("h2h_home_105"), 0)
    mkt_away = _safe_float(match.get("h2h_away_105"), 0)
    confluence_map = _load_confluence(CONFLUENCE_JSON)

    return {
        "sport": "NRL",
        "home": match["home_team"],
        "away": match["away_team"],
        "date": match.get("date", ""),
        "kickoff": match.get("kickoff", ""),
        "venue": match.get("venue", ""),
        "model": {
            "fair_home_odds": fair_home,
            "fair_away_odds": fair_away,
            "hcap_line": _safe_float(match.get("fair_hcap_line"), 0),
            "total_line": _safe_float(match.get("fair_total_line"), 0),
        },
        "market": {
            "h2h_home": mkt_home,
            "h2h_away": mkt_away,
        },
        "ev": {
            "home_h2h_pct": _ev_pct(fair_home, mkt_home),
            "away_h2h_pct": _ev_pct(fair_away, mkt_away),
        },
        "referee": match.get("referee", "TBC"),
        "ref_bucket": match.get("ref_bucket", "neutral"),
        "injuries": {
            "home": match.get("home_outs", ""),
            "away": match.get("away_outs", ""),
        },
        "weather": {
            "condition": match.get("weather_condition", ""),
            "temp_c": _safe_float(match.get("temp_c"), 0),
            "wind_kmh": _safe_float(match.get("wind_kmh"), 0),
        },
        "tier_adjustments": {
            "t1_note": match.get("t1_note", ""),
            "t2_note": match.get("t2_note", ""),
            "t3_note": match.get("t3_note", ""),
            "t4_note": match.get("t4_note", ""),
            "t5_note": match.get("t5_note", ""),
            "t6_note": match.get("t6_note", ""),
            "t7_note": match.get("t7_note", ""),
            "t8_note": match.get("t8_note", ""),
        },
        "explanation": match.get("explanation", ""),
        "confluence": confluence_map.get(match["home_team"].lower(), {}),
    }


def _context_game_afl(home: str, away: str) -> dict:
    pricing_csv = _latest_afl_pricing_csv()
    if not pricing_csv:
        raise HTTPException(status_code=503, detail="No AFL pricing file found")

    rows = _read_pricing_csv(pricing_csv)
    match = _find_game_row(rows, home, away)
    if not match:
        raise HTTPException(status_code=404, detail=f"AFL game not found: {home} vs {away}")

    rules_home = _safe_float(match.get("rules_home_odds"), 0)
    rules_away = _safe_float(match.get("rules_away_odds"), 0)
    rules_margin = _safe_float(match.get("rules_margin"), 0)
    rules_total = _safe_float(match.get("rules_total"), 0)
    ml_margin = _safe_float(match.get("ml_margin"), 0)
    ml_total = _safe_float(match.get("ml_total"), 0)
    ml_prob = _safe_float(match.get("ml_h2h"), 0)
    ml_home_odds = round(1 / ml_prob, 2) if ml_prob > 0.01 else 0
    ml_away_odds = round(1 / (1 - ml_prob), 2) if 0.01 < ml_prob < 0.99 else 0
    confluence_map = _load_confluence(AFL_CONFLUENCE_JSON)
    afl_injuries = _load_afl_injuries()
    injuries_home = _team_injury_str(afl_injuries, match["home_team"])
    injuries_away = _team_injury_str(afl_injuries, match["away_team"])

    return {
        "sport": "AFL",
        "home": match["home_team"],
        "away": match["away_team"],
        "date": match.get("game_date", ""),
        "kickoff": "",
        "venue": match.get("venue", ""),
        "model": {
            "fair_home_odds": rules_home,
            "fair_away_odds": rules_away,
            "hcap_line": rules_margin,
            "total_line": rules_total,
        },
        "ml_model": {
            "margin": ml_margin,
            "total": ml_total,
            "home_odds": ml_home_odds,
            "away_odds": ml_away_odds,
        },
        "market": {"h2h_home": 0, "h2h_away": 0},
        "ev": {"home_h2h_pct": 0, "away_h2h_pct": 0},
        "referee": "N/A",
        "ref_bucket": "",
        "injuries": {"home": injuries_home, "away": injuries_away},
        "weather": {"condition": "", "temp_c": 0, "wind_kmh": 0},
        "tier_adjustments": {},
        "explanation": match.get("explanation", ""),
        "confluence": confluence_map.get(match["home_team"].lower(), {}),
    }


@app.get("/context/team")
def context_team(team: str = Query(..., description="Team name")) -> dict:
    """Return team form, ELO, and injury status from DB."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not found")

    conn = _db()
    team_lower = f"%{team.lower()}%"

    team_row = _one(
        conn,
        "SELECT * FROM teams WHERE LOWER(team_name) LIKE ? LIMIT 1",
        (team_lower,),
    )
    if not team_row:
        raise HTTPException(status_code=404, detail=f"Team not found: {team}")

    team_id = team_row["team_id"]
    team_name = team_row["team_name"]

    # Last 5 results
    results = _rows(
        conn,
        """
        SELECT m.season, m.round_number, m.home_team_id, m.away_team_id,
               r.home_score, r.away_score
        FROM matches m
        JOIN results r ON r.match_id = m.match_id
        WHERE (m.home_team_id = ? OR m.away_team_id = ?)
          AND r.home_score IS NOT NULL
        ORDER BY m.season DESC, m.round_number DESC
        LIMIT 5
        """,
        (team_id, team_id),
    )

    form: list[str] = []
    for res in results:
        is_home = res["home_team_id"] == team_id
        team_score = res["home_score"] if is_home else res["away_score"]
        opp_score = res["away_score"] if is_home else res["home_score"]
        form.append("W" if team_score > opp_score else "L")

    # Current injuries from DB
    injuries = _rows(
        conn,
        """
        SELECT player_name, player_role, importance_tier, status
        FROM injury_reports
        WHERE team_id = ? AND status IN ('out', 'doubtful')
        ORDER BY
            CASE importance_tier WHEN 'elite' THEN 0 WHEN 'key' THEN 1 ELSE 2 END,
            CASE status WHEN 'out' THEN 0 ELSE 1 END
        LIMIT 10
        """,
        (team_id,),
    )

    return {
        "team": team_name,
        "last_5_form": form,
        "current_injuries": injuries,
    }


def _compute_matrix_and_totals(games: list[dict]) -> tuple[list[dict], list[dict]]:
    """Extract matrix signals (H2H + handicap aligned) and totals signals from game list."""
    matrix_signals: list[dict] = []
    totals_signals: list[dict] = []

    for g in games:
        conf = g.get("confluence", {})
        if not conf:
            continue

        entries = list(conf.items())
        h2h_clean = [(k, v) for k, v in entries if k.startswith("h2h_") and v.get("count", 0) >= 3]
        hcap_clean = [(k, v) for k, v in entries if k.startswith("handicap_") and v.get("count", 0) >= 3]
        totals_clean = [(k, v) for k, v in entries if k.startswith("totals_") and v.get("count", 0) >= 3]

        h2h_conflicted = len(h2h_clean) > 1
        hcap_conflicted = len(hcap_clean) > 1
        totals_conflicted = len(totals_clean) > 1

        h2h_side = None if len(h2h_clean) != 1 else ("HOME" if "HOME" in h2h_clean[0][0] else "AWAY")
        hcap_side = None if len(hcap_clean) != 1 else ("HOME" if "HOME" in hcap_clean[0][0] else "AWAY")
        aligned = h2h_side is not None and hcap_side is not None and h2h_side == hcap_side

        if not h2h_conflicted and not hcap_conflicted and aligned:
            top = sorted(h2h_clean + hcap_clean, key=lambda x: x[1]["count"], reverse=True)
            label = " | ".join(f"{v['count']}-way {k.replace('_', ' ')}" for k, v in top)
            matrix_signals.append({"home": g["home"], "away": g["away"], "label": label})

        if not totals_conflicted and len(totals_clean) > 0:
            top = sorted(totals_clean, key=lambda x: x[1]["count"], reverse=True)
            label = " | ".join(f"{v['count']}-way {k.replace('_', ' ')}" for k, v in top)
            ml_model = g.get("ml_model") or {}
            totals_signals.append({
                "home": g["home"], "away": g["away"],
                "label": label,
                "model_total": g.get("model_total", 0),
                "ml_total": ml_model.get("total"),
            })

    return matrix_signals, totals_signals


@app.get("/meta")
def meta(sport: str = Query(default="NRL")) -> dict:
    """Return round metadata only — fast call used to seed the system prompt."""
    try:
        if sport.upper() == "AFL":
            csv_path = _latest_afl_pricing_csv()
            if not csv_path:
                return {"round": "?", "season": "?", "sport": "AFL"}
            rows = _read_pricing_csv(csv_path)
            return {
                "round": rows[0].get("round_number", "?") if rows else "?",
                "season": rows[0].get("season", "?") if rows else "?",
                "sport": "AFL",
            }
        else:
            csv_path = _latest_pricing_csv()
            if not csv_path:
                return {"round": "?", "season": "?", "sport": "NRL"}
            rows = _read_pricing_csv(csv_path)
            return {
                "round": rows[0].get("round", "?") if rows else "?",
                "season": rows[0].get("season", "?") if rows else "?",
                "sport": "NRL",
            }
    except Exception:
        return {"round": "?", "season": "?", "sport": sport.upper()}


@app.get("/signals")
def signals(sport: str = Query(default="NRL")) -> dict:
    """Return matrix signals, totals signals, and H2H EV signals for the current round."""
    ctx = context_round(sport=sport)
    matrix_signals, totals_signals = _compute_matrix_and_totals(ctx["games"])
    games_summary = []
    for g in ctx["games"]:
        entry: dict = {
            "home": g["home"], "away": g["away"],
            "model_hcap": g["model_hcap"], "model_total": g["model_total"],
        }
        ml = g.get("ml_model")
        if ml:
            entry["ml_hcap"] = ml.get("margin")
            entry["ml_total"] = ml.get("total")
        if g.get("injuries", {}).get("home"):
            entry["injuries_home"] = g["injuries"]["home"]
        if g.get("injuries", {}).get("away"):
            entry["injuries_away"] = g["injuries"]["away"]
        games_summary.append(entry)
    return {
        "sport": ctx["sport"],
        "season": ctx["season"],
        "round": ctx["round"],
        "generated_at": ctx["generated_at"],
        "matrix_signals": matrix_signals,
        "totals_signals": totals_signals,
        "h2h_signals": ctx["signals"],
        "games_summary": games_summary,
    }


@app.get("/clv")
def clv(weeks: int = Query(4, ge=1, le=12)) -> dict:
    """Return CLV summary for recent rounds."""
    return _clv_summary(n_weeks=weeks)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "baz_server:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )
