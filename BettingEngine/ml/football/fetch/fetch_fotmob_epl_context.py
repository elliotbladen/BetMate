"""Fetch free FotMob EPL match context and confirmed lineup fields.

FotMob's public match pages contain serialized match statistics and lineups.
This keeps the raw provider payload out of the model: only match-level fields
needed for the historical context join are written.
"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "epl" / "context" / "fotmob_epl_match_context_2022_23_to_2025_26.csv"
REPORT = ROOT / "reports" / "fotmob_epl_context_audit.md"
LEAGUE_URL = "https://www.fotmob.com/api/data/leagues?id=47&season={season}"
PAGE_URL = "https://www.fotmob.com/match/{match_id}"
SEASONS = ["2022/2023", "2023/2024", "2024/2025", "2025/2026"]
SEASON_LABEL = {"2022/2023": "2022/23", "2023/2024": "2023/24", "2024/2025": "2024/25", "2025/2026": "2025/26"}
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "text/html"}


def _value(stats: dict, key: str):
    if not isinstance(stats, dict):
        return None, None
    for group in stats.get("Periods", {}).get("All", {}).get("stats", []):
        for item in group.get("stats", []):
            if item.get("key") == key:
                vals = item.get("stats", [None, None])
                return vals[0], vals[1]
    return None, None


def _parse_match(item: dict) -> dict | None:
    mid = str(item["id"])
    try:
        html = requests.get(PAGE_URL.format(match_id=mid), headers=HEADERS, timeout=15).text
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if not m:
            return None
        page = json.loads(m.group(1))["props"]["pageProps"]
        general, content = page["general"], page["content"]
        stats = content.get("stats") or {}
        out = {
            "fotmob_match_id": mid,
            "date": general.get("matchTimeUTCDate", "")[:10],
            "home_team": general.get("homeTeam", {}).get("name"),
            "away_team": general.get("awayTeam", {}).get("name"),
            "home_formation": content.get("lineup", {}).get("homeTeam", {}).get("formation"),
            "away_formation": content.get("lineup", {}).get("awayTeam", {}).get("formation"),
        }
        keys = {
            "possession": "BallPossesion", "xg": "expected_goals",
            "shots": "total_shots", "shots_on_target": "ShotsOnTarget",
            "blocked_shots": "blocked_shots", "shots_inside_box": "shots_inside_box",
            "accurate_crosses": "accurate_crosses", "touches_opp_box": "touches_opp_box",
            "final_third_passes": "passes_into_final_third", "corners": "corners",
            "fouls": "fouls", "yellow_cards": "yellow_cards",
        }
        for name, key in keys.items():
            h, a = _value(stats, key)
            out[f"home_{name}"], out[f"away_{name}"] = h, a
        for side, team_key in [("home", "homeTeam"), ("away", "awayTeam")]:
            team = content.get("lineup", {}).get(team_key, {})
            starters = team.get("starters", [])
            ratings = [p.get("performance", {}).get("rating") for p in starters]
            ratings = [float(x) for x in ratings if x is not None]
            out[f"{side}_starter_count"] = len(starters)
            out[f"{side}_starter_rating_mean"] = sum(ratings) / len(ratings) if ratings else None
            out[f"{side}_lineup_source"] = content.get("lineup", {}).get("source")
        return out
    except Exception:
        return None


def main() -> None:
    all_matches = []
    for season in SEASONS:
        label = SEASON_LABEL[season]
        data = requests.get(LEAGUE_URL.format(season=season), headers=HEADERS, timeout=30).json()
        all_matches.extend([{**m, "season": label} for m in data.get("fixtures", {}).get("allMatches", []) if m.get("status", {}).get("finished")])
    all_matches = {str(m["id"]): m for m in all_matches}.values()
    rows = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = {pool.submit(_parse_match, m): m for m in all_matches}
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            if row:
                row["season"] = futs[fut]["season"]
                rows.append(row)
            if i % 100 == 0:
                print(f"parsed {i}/{len(futs)}", flush=True)
    out = pd.DataFrame(rows).sort_values(["season", "date", "home_team"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    fields = [c for c in out if c.startswith("home_") or c.startswith("away_")]
    cov = out.groupby("season")[fields].apply(lambda x: x.notna().mean()).round(3)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("# FotMob EPL context audit\n\nRows: %d\n\n" % len(out) + cov.to_string() + "\n")
    print(f"Saved {len(out)} rows to {OUT}")


if __name__ == "__main__":
    main()
