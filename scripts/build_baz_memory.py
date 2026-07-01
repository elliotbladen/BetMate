#!/usr/bin/env python3
"""
Build Baz's historical game memory from local BetMate outputs.

This produces a sanitized memory layer for product use:
- model lines/prices
- market open/close summaries
- weather/ref/injury state
- results and CLV review rows
- actual bet outcomes

It intentionally does not copy model formulas, raw workbooks, code, prompts, or
private pipeline details into the output.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "BettingEngine"
OUT_DIR = ROOT / "data" / "baz_memory"

ODDS_ROW_LIMIT = 120
CLV_ROW_LIMIT = 40
BET_ROW_LIMIT = 20


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "unknown"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def load_env() -> None:
    env_path = ROOT / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def push_data_store_key(key: str, data: dict[str, Any]) -> None:
    import requests

    load_env()
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    svc_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not svc_key:
        raise RuntimeError("NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing")

    payload = [{
        "key": key,
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }]
    resp = requests.post(
        f"{url}/rest/v1/betmate_data_store",
        headers={
            "apikey": svc_key,
            "Authorization": f"Bearer {svc_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()


def game_id(sport: str, season: Any, round_number: Any, date: Any, home: Any, away: Any) -> str:
    del date
    return (
        f"{sport.lower()}-{season or 'unknown'}-r{round_number or 'unknown'}-"
        f"{slug(home)}-v-{slug(away)}"
    )


def pair_key(home: Any, away: Any) -> tuple[str, str]:
    return norm(home), norm(away)


def detect_sport_from_pricing(path: Path, row: dict[str, str]) -> str | None:
    path_text = str(path).lower()
    if "\\nrl\\" in path_text or "/nrl/" in path_text or "nrl" in path.name.lower():
        return "NRL"
    if "\\afl\\" in path_text or "/afl/" in path_text or "afl" in path.name.lower():
        return "AFL"
    if "round_number" in row or "rules_margin" in row or "rules_home_odds" in row:
        return "AFL"
    if "fair_home_odds" in row or "fair_hcap_line" in row:
        return "NRL"
    return None


def merge_record(records: dict[str, dict[str, Any]], record: dict[str, Any]) -> None:
    rid = record["id"]
    existing = records.setdefault(rid, record)
    if existing is record:
        return

    for key, value in record.items():
        if value in (None, "", [], {}):
            continue
        if key not in existing or existing[key] in (None, "", [], {}):
            existing[key] = value
        elif isinstance(existing.get(key), dict) and isinstance(value, dict):
            existing[key] = {**existing[key], **{k: v for k, v in value.items() if v not in (None, "", [], {})}}


def pricing_record_from_row(path: Path, row: dict[str, str]) -> dict[str, Any] | None:
    sport = detect_sport_from_pricing(path, row)
    if not sport:
        return None

    season = row.get("season") or "2026"
    round_number = row.get("round") or row.get("round_number")
    date = row.get("date") or row.get("game_date")
    home = row.get("home_team")
    away = row.get("away_team")
    if not home or not away:
        return None

    if sport == "AFL":
        model = {
            "home_odds": safe_float(row.get("rules_home_odds")),
            "away_odds": safe_float(row.get("rules_away_odds")),
            "margin": safe_float(row.get("rules_margin")),
            "total": safe_float(row.get("rules_total")),
        }
        ml_model = {
            "margin": safe_float(row.get("ml_margin")),
            "total": safe_float(row.get("ml_total")),
            "home_probability": safe_float(row.get("ml_h2h")),
        }
        market_at_pricing = {}
        weather = {
            "condition": row.get("weather_condition"),
            "temp_c": safe_float(row.get("temp_c")),
            "wind_kmh": safe_float(row.get("wind_kmh")),
            "wind_gust_kmh": safe_float(row.get("wind_gust_kmh")),
            "precip_mm": safe_float(row.get("precip_mm")),
            "source": row.get("weather_source"),
        }
        result = {
            "home_score": safe_int(row.get("actual_home")),
            "away_score": safe_int(row.get("actual_away")),
            "margin_home": safe_float(row.get("actual_margin")),
            "total": safe_float(row.get("actual_total")),
        }
    else:
        model = {
            "home_odds": safe_float(row.get("fair_home_odds")),
            "away_odds": safe_float(row.get("fair_away_odds")),
            "margin": safe_float(row.get("fair_hcap_line")),
            "total": safe_float(row.get("fair_total_line")),
        }
        ml_model = {}
        market_at_pricing = {
            "h2h_home": safe_float(row.get("h2h_home_105")),
            "h2h_away": safe_float(row.get("h2h_away_105")),
            "handicap_line": safe_float(row.get("hcap_line_105")),
            "handicap_price": safe_float(row.get("hcap_price_105")),
            "total_line": safe_float(row.get("total_line_105")),
            "total_price": safe_float(row.get("total_price_105")),
        }
        weather = {
            "condition": row.get("weather_condition"),
            "temp_c": safe_float(row.get("temp_c")),
            "wind_kmh": safe_float(row.get("wind_kmh")),
        }
        result = {
            "home_score": safe_int(row.get("actual_home")),
            "away_score": safe_int(row.get("actual_away")),
            "total": safe_float(row.get("actual_total")),
        }

    return {
        "id": game_id(sport, season, round_number, date, home, away),
        "sport": sport,
        "season": safe_int(season) or season,
        "round": safe_int(round_number) or round_number,
        "date": str(date or "")[:10],
        "kickoff": row.get("kickoff", ""),
        "home": home,
        "away": away,
        "venue": row.get("venue", ""),
        "model": model,
        "ml_model": ml_model,
        "market_at_pricing": market_at_pricing,
        "weather": {k: v for k, v in weather.items() if v not in (None, "")},
        "referee": row.get("referee") or ("N/A" if sport == "AFL" else ""),
        "ref_bucket": row.get("ref_bucket", ""),
        "injuries": {
            "home": row.get("home_outs", ""),
            "away": row.get("away_outs", ""),
        },
        "result": {k: v for k, v in result.items() if v is not None},
        "source_files": {"pricing": str(path.relative_to(ROOT))},
    }


def load_pricing_records(year: int) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    candidates = [
        *ENGINE.glob(f"results/r*_pricing_{year}.csv"),
        *ENGINE.glob(f"results/r*_afl_{year}.csv"),
        *ENGINE.glob(f"data/pricing/nrl/*{year}*.csv"),
        *ENGINE.glob(f"data/pricing/afl/*{year}*.csv"),
        *ENGINE.glob(f"outputs/afl_round_prep/r*_{year}/afl_r*_pricing_{year}.csv"),
    ]
    base_pricing_files = [
        path for path in sorted(set(candidates))
        if "ml_shadow" not in path.name.lower()
        and "tier_breakdown" not in path.name.lower()
        and "comparison" not in path.name.lower()
    ]
    for path in base_pricing_files:
        for row in read_csv(path):
            record = pricing_record_from_row(path, row)
            if record:
                merge_record(records, record)
    return records


def load_results(year: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ENGINE / "data" / "import").glob(f"r*_results_{year}.csv")):
        for row in read_csv(path):
            rows.append({
                "source": str(path.relative_to(ROOT)),
                "home": row.get("home_team"),
                "away": row.get("away_team"),
                "date": str(row.get("match_date") or "")[:10],
                "home_score": safe_int(row.get("home_score")),
                "away_score": safe_int(row.get("away_score")),
            })
    return rows


def apply_results(records: dict[str, dict[str, Any]], results: list[dict[str, Any]]) -> None:
    by_pair_date = {
        (pair_key(row["home"], row["away"]), row["date"]): row
        for row in results
        if row.get("home") and row.get("away")
    }
    for record in records.values():
        key = (pair_key(record["home"], record["away"]), record.get("date", ""))
        result = by_pair_date.get(key)
        if not result:
            continue
        home_score = result.get("home_score")
        away_score = result.get("away_score")
        if home_score is None or away_score is None:
            continue
        record["result"] = {
            "home_score": home_score,
            "away_score": away_score,
            "margin_home": home_score - away_score,
            "total": home_score + away_score,
        }
        record.setdefault("source_files", {})["result"] = result["source"]


def load_clv_rows(year: int) -> dict[tuple[str, int, int, str, str], list[dict[str, Any]]]:
    by_game: dict[tuple[str, int, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    paths = [
        *ENGINE.glob(f"outputs/nrl_weekly_review/reports/r*_nrl_clv_report_{year}.csv"),
        *ENGINE.glob(f"outputs/afl_weekly_review/reports/r*_afl_ml_clv_comparison_{year}.csv"),
        *ENGINE.glob(f"data/clv/nrl/*{year}*.csv"),
        *ENGINE.glob(f"data/clv/afl/*{year}*.csv"),
    ]
    for path in sorted(set(paths)):
        sport = "AFL" if "afl" in path.name.lower() or "\\afl\\" in str(path).lower() else "NRL"
        for row in read_csv(path):
            season = safe_int(row.get("season")) or year
            round_number = safe_int(row.get("round"))
            home = row.get("home_team")
            away = row.get("away_team")
            if not round_number or not home or not away:
                continue
            compact = {
                "market": row.get("market"),
                "signal": row.get("signal"),
                "selection": row.get("selection"),
                "model_number": safe_float(row.get("model_number")),
                "model_home_fair_odds": safe_float(row.get("model_home_fair_odds")),
                "model_away_fair_odds": safe_float(row.get("model_away_fair_odds")),
                "open_number": safe_float(row.get("open_number")),
                "close_number": safe_float(row.get("close_number")),
                "open_odds": safe_float(row.get("open_odds")),
                "close_odds": safe_float(row.get("close_odds")),
                "clv": safe_float(row.get("clv")),
                "result": row.get("result"),
                "winner": row.get("winner"),
                "bookmakers_surveyed": safe_int(row.get("bookmakers_surveyed")),
                "source": str(path.relative_to(ROOT)),
            }
            by_game[(sport, season, round_number, norm(home), norm(away))].append(
                {k: v for k, v in compact.items() if v not in (None, "")}
            )
    return by_game


def apply_clv(records: dict[str, dict[str, Any]], clv_rows: dict[tuple[str, int, int, str, str], list[dict[str, Any]]]) -> None:
    for record in records.values():
        key = (
            record["sport"],
            safe_int(record["season"]) or 0,
            safe_int(record["round"]) or 0,
            norm(record["home"]),
            norm(record["away"]),
        )
        rows = clv_rows.get(key, [])[:CLV_ROW_LIMIT]
        if rows:
            record["clv_review"] = rows


def load_bets(year: int) -> dict[tuple[str, int, int, str, str], list[dict[str, Any]]]:
    path = ENGINE / "data" / "bets" / f"actual_bets_{year}.csv"
    by_game: dict[tuple[str, int, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv(path):
        sport = str(row.get("sport") or "").upper()
        season = safe_int(row.get("season")) or year
        round_number = safe_int(row.get("round"))
        home = row.get("home_team")
        away = row.get("away_team")
        if not sport or not round_number or not home or not away:
            continue
        compact = {
            "bet_id": row.get("bet_id"),
            "placed_date": row.get("placed_date"),
            "market_type": row.get("market_type"),
            "selection": row.get("selection"),
            "line": safe_float(row.get("line")),
            "odds_taken": safe_float(row.get("odds_taken")),
            "stake": safe_float(row.get("stake")),
            "result": row.get("result"),
            "pnl": safe_float(row.get("pnl")),
            "bookmaker": row.get("bookmaker"),
            "model_price": safe_float(row.get("model_price")),
            "model_line": safe_float(row.get("model_line")),
            "closing_price": safe_float(row.get("closing_price")),
            "closing_line": safe_float(row.get("closing_line")),
            "clv": safe_float(row.get("clv")),
        }
        by_game[(sport, season, round_number, norm(home), norm(away))].append(
            {k: v for k, v in compact.items() if v not in (None, "")}
        )
    return by_game


def apply_bets(records: dict[str, dict[str, Any]], bets: dict[tuple[str, int, int, str, str], list[dict[str, Any]]]) -> None:
    for record in records.values():
        key = (
            record["sport"],
            safe_int(record["season"]) or 0,
            safe_int(record["round"]) or 0,
            norm(record["home"]),
            norm(record["away"]),
        )
        rows = bets.get(key, [])[:BET_ROW_LIMIT]
        if rows:
            record["actual_bets"] = rows
            record["bet_summary"] = {
                "bets": len(rows),
                "pnl": round(sum(float(row.get("pnl", 0)) for row in rows), 2),
                "stake": round(sum(float(row.get("stake", 0)) for row in rows), 2),
            }


def snapshot_datetime(row: dict[str, str]) -> str:
    return f"{row.get('snapshot_date', '')}T{row.get('snapshot_time', '00:00:00')}"


def sanitize_odds_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "snapshot_date": row.get("snapshot_date"),
        "snapshot_time": row.get("snapshot_time"),
        "bookmaker": row.get("bookmaker"),
        "market": row.get("market"),
        "outcome": row.get("outcome"),
        "price": safe_float(row.get("price")),
        "point": safe_float(row.get("point")),
    }


def load_odds_rows(year: int) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    by_game: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for path in sorted((ROOT / "data" / "odds_snapshots" / str(year)).glob("*.csv")):
        for row in read_csv(path):
            sport = str(row.get("sport") or "").upper()
            home = row.get("home_team")
            away = row.get("away_team")
            if sport in {"NRL", "AFL"} and home and away:
                row["_source"] = str(path.relative_to(ROOT))
                by_game[(sport, norm(home), norm(away))].append(row)
    return by_game


def apply_odds(records: dict[str, dict[str, Any]], odds_rows: dict[tuple[str, str, str], list[dict[str, str]]]) -> None:
    for record in records.values():
        rows = odds_rows.get((record["sport"], norm(record["home"]), norm(record["away"])), [])
        if not rows:
            continue
        rows = sorted(rows, key=snapshot_datetime)
        opening_dt = snapshot_datetime(rows[0])
        closing_dt = snapshot_datetime(rows[-1])
        opening = [sanitize_odds_row(row) for row in rows if snapshot_datetime(row) == opening_dt][:ODDS_ROW_LIMIT]
        closing = [sanitize_odds_row(row) for row in rows if snapshot_datetime(row) == closing_dt][:ODDS_ROW_LIMIT]
        record["bookmaker_prices"] = {
            "first_snapshot_at": opening_dt,
            "latest_snapshot_at": closing_dt,
            "bookmakers_observed": sorted({row.get("bookmaker", "") for row in rows if row.get("bookmaker")}),
            "opening_rows": opening,
            "latest_rows": closing,
            "rows_observed": len(rows),
        }


def classify_angle(record: dict[str, Any]) -> str:
    if record.get("actual_bets"):
        pnl = record.get("bet_summary", {}).get("pnl", 0)
        if pnl > 0:
            return "bet_won"
        if pnl < 0:
            return "bet_lost"
        return "bet_even"
    if record.get("clv_review"):
        positive = [row for row in record["clv_review"] if (row.get("clv") or 0) > 0]
        negative = [row for row in record["clv_review"] if (row.get("clv") or 0) < 0]
        if positive and len(positive) >= len(negative):
            return "model_review_positive_clv"
        if negative:
            return "model_review_negative_clv"
    return "no_bet_or_untracked"


def finalize(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    finalized = []
    for record in records.values():
        record["angle_outcome"] = classify_angle(record)
        finalized.append(record)
    return sorted(finalized, key=lambda item: (str(item.get("date")), item.get("sport", ""), item.get("home", "")))


def build_memory(year: int) -> dict[str, Any]:
    records = load_pricing_records(year)
    apply_results(records, load_results(year))
    apply_clv(records, load_clv_rows(year))
    apply_bets(records, load_bets(year))
    apply_odds(records, load_odds_rows(year))
    games = finalize(records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "year": year,
        "safety": {
            "public_blob": False,
            "sanitized_for_baz_product": True,
            "contains_engine_code": False,
            "contains_model_weights": False,
            "contains_raw_database": False,
            "contains_matrix_workbooks": False,
        },
        "counts": {
            "games": len(games),
            "with_results": sum(1 for game in games if game.get("result")),
            "with_clv_review": sum(1 for game in games if game.get("clv_review")),
            "with_actual_bets": sum(1 for game in games if game.get("actual_bets")),
            "with_bookmaker_prices": sum(1 for game in games if game.get("bookmaker_prices")),
        },
        "games": games,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sanitized Baz historical game memory.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--push-supabase", action="store_true", help="Publish sanitized memory to betmate_data_store.")
    args = parser.parse_args()

    payload = build_memory(args.year)
    year_path = OUT_DIR / str(args.year) / "game_memory.json"
    latest_path = OUT_DIR / "latest_game_memory.json"
    write_json(year_path, payload)
    write_json(latest_path, payload)
    print(f"Wrote {year_path.relative_to(ROOT)}")
    print(f"Wrote {latest_path.relative_to(ROOT)}")
    print(json.dumps(payload["counts"], indent=2, sort_keys=True))
    if args.push_supabase:
        push_data_store_key(f"baz_memory_{args.year}", payload)
        push_data_store_key("baz_memory_latest", payload)
        print(f"Pushed Supabase keys: baz_memory_{args.year}, baz_memory_latest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
