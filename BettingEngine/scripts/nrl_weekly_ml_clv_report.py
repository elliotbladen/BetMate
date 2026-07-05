#!/usr/bin/env python3
"""
Build a weekly NRL ML-shadow comparison report.

Compares three signals against the same opening/closing market and actuals:
  - ml: ML shadow adjusted prices/lines
  - normal: the rules/pricing engine
  - market: the market's open-to-close move

Output:
  outputs/nrl_weekly_review/reports/r{round}_nrl_ml_comparison_{season}.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

import nrl_weekly_clv_report as clv


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
DEFAULT_REPORT_DIR = ROOT / "outputs" / "nrl_weekly_review" / "reports"
DEFAULT_ML_DIR = ROOT / "outputs" / "nrl_weekly_review" / "ml_shadow"

SHORT_TEAM = {
    "Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Cowboys": "North Queensland Cowboys",
    "Dolphins": "Dolphins",
    "Storm": "Melbourne Storm",
    "Titans": "Gold Coast Titans",
    "Raiders": "Canberra Raiders",
    "Eels": "Parramatta Eels",
    "Warriors": "New Zealand Warriors",
    "Roosters": "Sydney Roosters",
    "Broncos": "Brisbane Broncos",
    "Knights": "Newcastle Knights",
    "Rabbitohs": "South Sydney Rabbitohs",
    "Sharks": "Cronulla-Sutherland Sharks",
    "Tigers": "Wests Tigers",
    "Panthers": "Penrith Panthers",
    "Eagles": "Manly-Warringah Sea Eagles",
    "Dragons": "St. George Illawarra Dragons",
}


def latest_completed_round(season: int) -> int:
    return clv.auto_round(season)


def find_ml_shadow_path(season: int, rnd: int) -> Path:
    candidates = [
        DEFAULT_ML_DIR / f"r{rnd}_ml_shadow_{season}.txt",
        DEFAULT_ML_DIR / f"r{rnd:02d}_ml_shadow_{season}.txt",
        RESULTS_DIR / f"r{rnd}_ml_shadow_{season}.txt",
        RESULTS_DIR / f"r{rnd:02d}_ml_shadow_{season}.txt",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise SystemExit(
        f"No ML shadow file found for R{rnd} {season}. Expected one of: "
        + ", ".join(str(p) for p in candidates)
    )


def parse_num(raw: str) -> float:
    cleaned = raw.replace("%", "").replace("▲", "").replace("▼", "").replace("—", "").strip()
    return float(cleaned)


def full_game_name(game: str) -> tuple[str, str]:
    left, right = [part.strip() for part in game.split(" vs ", 1)]
    if left not in SHORT_TEAM or right not in SHORT_TEAM:
        raise SystemExit(f"Unknown ML shadow team label: {game}")
    return SHORT_TEAM[left], SHORT_TEAM[right]


def parse_ml_shadow(path: Path) -> dict[tuple[str, str], dict[str, float]]:
    rows: dict[tuple[str, str], dict[str, float]] = {}
    section = ""
    pattern = re.compile(r"^\s{2}([A-Za-z. ]+ vs [A-Za-z. ]+)\s+(.+)$")

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("MARGIN"):
            section = "margin"
            continue
        if line.strip().startswith("TOTAL"):
            section = "total"
            continue
        if line.strip().startswith("H2H WIN PROBABILITY"):
            section = "h2h"
            continue
        if line.strip().startswith("FEATURE AUDIT") or line.strip().startswith("DIVERGENCE SUMMARY"):
            section = ""
            continue
        if not section or " vs " not in line:
            continue

        match = pattern.match(line)
        if not match:
            continue
        home, away = full_game_name(match.group(1).strip())
        nums = match.group(2).split()
        rec = rows.setdefault((home, away), {})

        if section == "margin":
            # ELO, ML raw, T2, T5, T7, ML adjusted, rules, diff
            rec["ml_margin"] = parse_num(nums[5])
            rec["normal_margin_from_shadow"] = parse_num(nums[6])
        elif section == "total":
            # ML raw, T5, T7, ML adjusted, rules, diff
            rec["ml_total"] = parse_num(nums[3])
            rec["normal_total_from_shadow"] = parse_num(nums[4])
        elif section == "h2h":
            # ML raw %, ML adjusted %, rules %, diff %, ML odds, rules odds
            rec["ml_home_prob"] = parse_num(nums[1]) / 100.0
            rec["normal_home_prob_from_shadow"] = parse_num(nums[2]) / 100.0
            rec["ml_home_fair_odds"] = parse_num(nums[4])

    return rows


def h2h_selection_from_home_prob(home: str, away: str, prob: float | None) -> str:
    if prob is None:
        return ""
    return home if prob >= 0.5 else away


def fair_odds_from_prob(selection: str, home: str, away: str, home_prob: float | None) -> tuple[float | None, float | None, float | None]:
    if home_prob is None or home_prob <= 0 or home_prob >= 1:
        return None, None, None
    home_odds = round(1.0 / home_prob, 3)
    away_odds = round(1.0 / (1.0 - home_prob), 3)
    selected = home_odds if selection == home else away_odds if selection == away else None
    return home_odds, away_odds, selected


def market_h2h_selection(home: str, away: str, market: dict[str, Any]) -> str:
    return clv.h2h_market_move(home, away, market)


def build_rows(season: int, rnd: int, ml_path: Path) -> list[dict[str, Any]]:
    pricing_rows = clv.load_csv(clv.pricing_path(season, rnd))
    actual_rows = clv.load_csv(clv.IMPORT_DIR / f"r{rnd}_results_{season}.csv")
    workbook_rows = clv.load_workbook_rows(clv.DEFAULT_WORKBOOK, season)
    ml_rows = parse_ml_shadow(ml_path)

    actual_by_match = {
        (clv.as_date(r.get("match_date")), clv.canon_team(r["home_team"]), clv.canon_team(r["away_team"])): r
        for r in actual_rows
    }

    out: list[dict[str, Any]] = []
    for p in pricing_rows:
        match_date = clv.as_date(p["date"])
        home = clv.canon_team(p["home_team"])
        away = clv.canon_team(p["away_team"])
        key = (match_date, home, away)
        ml_key = (home, away)
        if key not in actual_by_match:
            raise SystemExit(f"No actual result found for {match_date} {home} vs {away}")
        if key not in workbook_rows:
            raise SystemExit(f"No workbook row found for {match_date} {home} vs {away}")
        if ml_key not in ml_rows:
            raise SystemExit(f"No ML shadow row found for {home} vs {away} in {ml_path}")

        actual = actual_by_match[key]
        market = workbook_rows[key]
        ml = ml_rows[ml_key]
        home_score = float(actual["home_score"])
        away_score = float(actual["away_score"])
        actual_total = home_score + away_score
        actual_margin = home_score - away_score

        normal_margin = clv.as_float(p.get("final_margin"))
        normal_total = clv.as_float(p.get("final_total"))
        normal_home_odds = clv.as_float(p.get("fair_home_odds"))
        normal_away_odds = clv.as_float(p.get("fair_away_odds"))
        normal_home_prob = (1 / normal_home_odds) if normal_home_odds else None

        common = {
            "season": season,
            "round": rnd,
            "date": match_date.isoformat() if match_date else "",
            "home_team": home,
            "away_team": away,
            "home_score": int(home_score),
            "away_score": int(away_score),
            "actual_margin_home": actual_margin,
            "actual_total": actual_total,
        }

        signals = {
            "ml": {
                "margin": ml.get("ml_margin"),
                "total": ml.get("ml_total"),
                "home_prob": ml.get("ml_home_prob"),
            },
            "normal": {
                "margin": normal_margin,
                "total": normal_total,
                "home_prob": normal_home_prob,
            },
            "market": {},
        }

        # H2H
        for signal, values in signals.items():
            if signal == "market":
                selection = market_h2h_selection(home, away, market)
                home_fair = away_fair = selected_fair = ""
            else:
                selection = h2h_selection_from_home_prob(home, away, values.get("home_prob"))
                home_fair, away_fair, selected_fair = fair_odds_from_prob(selection, home, away, values.get("home_prob"))
            open_odds = clv.odds_for_selection(market, selection, home, away, "Open")
            close_odds = clv.odds_for_selection(market, selection, home, away, "Close")
            out.append({
                **common,
                "market": "h2h",
                "signal": signal,
                "selection": selection,
                "model_number": "",
                "model_home_fair_odds": home_fair,
                "model_away_fair_odds": away_fair,
                "model_selected_fair_odds": selected_fair,
                "open_number": "",
                "close_number": "",
                "open_odds": open_odds,
                "close_odds": close_odds,
                "clv": clv.decimal_clv(open_odds, close_odds),
                "result": clv.h2h_result(selection, home, away, home_score, away_score),
            })

        # Handicap
        home_line_open = clv.as_float(market.get("Home Line Open"))
        for signal, values in signals.items():
            if signal == "market":
                selection = clv.handicap_market_move(home, away, market)
                model_number = ""
            else:
                selection = clv.handicap_pick(values.get("margin"), home_line_open, home, away)
                model_number = values.get("margin")
            open_line = clv.line_for_selection(market, selection, home, away, "Open")
            close_line = clv.line_for_selection(market, selection, home, away, "Close")
            out.append({
                **common,
                "market": "handicap",
                "signal": signal,
                "selection": selection,
                "model_number": model_number,
                "model_home_fair_odds": "",
                "model_away_fair_odds": "",
                "model_selected_fair_odds": "",
                "open_number": open_line,
                "close_number": close_line,
                "open_odds": clv.line_for_selection_odds(market, selection, home, away, "Open"),
                "close_odds": clv.line_for_selection_odds(market, selection, home, away, "Close"),
                "clv": clv.handicap_clv(selection, open_line, close_line),
                "result": clv.spread_result(selection, home, away, home_score, away_score, open_line),
            })

        # Totals
        total_open = clv.as_float(market.get("Total Score Open"))
        total_close = clv.as_float(market.get("Total Score Close"))
        for signal, values in signals.items():
            if signal == "market":
                selection = clv.total_market_move(market)
                model_number = ""
            else:
                selection = clv.total_pick(values.get("total"), total_open)
                model_number = values.get("total")
            out.append({
                **common,
                "market": "total",
                "signal": signal,
                "selection": selection,
                "model_number": model_number,
                "model_home_fair_odds": "",
                "model_away_fair_odds": "",
                "model_selected_fair_odds": "",
                "open_number": total_open,
                "close_number": total_close,
                "open_odds": clv.total_odds(market, selection, "Open"),
                "close_odds": clv.total_odds(market, selection, "Close"),
                "clv": clv.total_line_clv(selection, total_open, total_close),
                "result": clv.total_result(selection, actual_total, total_open),
            })

    add_winners(out)
    return out


def add_winners(rows: list[dict[str, Any]]) -> None:
    score = {"win": 1, "push": 0, "loss": -1, "": 0}
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (row["date"], row["home_team"], row["away_team"], row["market"])
        grouped.setdefault(key, {})[row["signal"]] = row

    for group in grouped.values():
        ordered = sorted(
            group.values(),
            key=lambda r: (score.get(r.get("result", ""), 0), float(r["clv"]) if r.get("clv") not in ("", None) else -999.0),
            reverse=True,
        )
        best_score = score.get(ordered[0].get("result", ""), 0)
        best_clv = float(ordered[0]["clv"]) if ordered[0].get("clv") not in ("", None) else -999.0
        winners = [
            r["signal"] for r in ordered
            if score.get(r.get("result", ""), 0) == best_score
            and (float(r["clv"]) if r.get("clv") not in ("", None) else -999.0) == best_clv
        ]
        value = "tie" if len(winners) > 1 else winners[0]
        for row in group.values():
            row["winner"] = value


def write_report(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "season", "round", "date", "home_team", "away_team",
        "home_score", "away_score", "actual_margin_home", "actual_total",
        "market", "signal", "selection",
        "model_number", "model_home_fair_odds", "model_away_fair_odds", "model_selected_fair_odds",
        "open_number", "close_number", "open_odds", "close_odds",
        "clv", "result", "winner",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, Any]], out_path: Path) -> None:
    from collections import Counter

    print(f"Written {len(rows)} rows -> {out_path}")
    for signal in ("ml", "normal", "market"):
        print(f"{signal:>6}: {dict(Counter(r['result'] for r in rows if r['signal'] == signal))}")
    print(f"winner: {dict(Counter(r['winner'] for r in rows if r['signal'] == 'ml'))}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build NRL weekly ML-shadow comparison report.")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--round", type=int, default=0, dest="round_number", help="0 = latest completed round")
    parser.add_argument("--ml-shadow", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rnd = args.round_number or latest_completed_round(args.season)
    ml_path = args.ml_shadow or find_ml_shadow_path(args.season, rnd)
    out_path = args.out or DEFAULT_REPORT_DIR / f"r{rnd}_nrl_ml_comparison_{args.season}.csv"
    rows = build_rows(args.season, rnd, ml_path)
    write_report(rows, out_path)
    print_summary(rows, out_path)


if __name__ == "__main__":
    main()
