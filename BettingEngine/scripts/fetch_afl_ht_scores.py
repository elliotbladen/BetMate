"""
scripts/fetch_afl_ht_scores.py

Scrape AFL quarter-by-quarter scores from afltables.com (2022–2026) and join
to the AFL halftime Betfair dataset, populating ht_home_score / ht_away_score.

afltables HTML structure (each match is a <table> with 2 <tr> rows):
  Row 1 (home): <a>TeamName</a>  <tt>Q1 Q2 Q3 Q4</tt>  FT  Date/Venue
  Row 2 (away): <a>TeamName</a>  <tt>Q1 Q2 Q3 Q4</tt>  FT  Result

Q2 cumulative score (goals.behinds) = halftime score.
Points = goals * 6 + behinds.

Usage:
    uv run python scripts/fetch_afl_ht_scores.py
    uv run python scripts/fetch_afl_ht_scores.py --years 2024 2025 2026
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd
import requests

YEARS = [2022, 2023, 2024, 2025, 2026]
AFLTABLES_URL = "https://afltables.com/afl/seas/{year}.html"

_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = _ROOT / "data" / "inplay" / "afl" / "halftime" / "processed" / "halftime_dataset.csv"
HT_SCORES_PATH = _ROOT / "data" / "inplay" / "afl" / "halftime" / "raw" / "ht_scores_afltables.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*",
}

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

TEAM_NAME_MAP = {
    "Adelaide":               "Adelaide",
    "Brisbane Lions":         "Brisbane",
    "Brisbane":               "Brisbane",
    "Carlton":                "Carlton",
    "Collingwood":            "Collingwood",
    "Essendon":               "Essendon",
    "Fremantle":              "Fremantle",
    "Geelong":                "Geelong",
    "Gold Coast":             "Gold Coast",
    "Greater Western Sydney": "GWS",
    "GW Sydney":              "GWS",
    "Hawthorn":               "Hawthorn",
    "Melbourne":              "Melbourne",
    "North Melbourne":        "North Melbourne",
    "Port Adelaide":          "Port Adelaide",
    "Richmond":               "Richmond",
    "St Kilda":               "St Kilda",
    "Sydney":                 "Sydney",
    "West Coast":             "West Coast",
    "Western Bulldogs":       "Western Bulldogs",
}


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def parse_score_str(score_str: str) -> tuple[int, int, int]:
    """'6.9' → (goals, behinds, points)"""
    g, b = score_str.strip().split(".")
    g, b = int(g), int(b)
    return g, b, g * 6 + b


def parse_date(date_str: str) -> str | None:
    """'14-Mar-2024' → '2024-03-14'"""
    try:
        parts = date_str.strip().split("-")
        d, mon, y = parts
        m = MONTH_MAP.get(mon)
        if m is None:
            return None
        return f"{y}-{m:02d}-{int(d):02d}"
    except Exception:
        return None


def normalise_team(name: str) -> str:
    name = name.strip()
    return TEAM_NAME_MAP.get(name, name)


def extract_scores_from_tt(tt_html: str) -> list[str] | None:
    """
    Extract 4 quarter scores from <tt> cell content like:
    '&nbsp;&nbsp;3.3 &nbsp;&nbsp;6.9 &nbsp;9.11 12.14 '
    Returns list of 4 score strings ['3.3', '6.9', '9.11', '12.14'] or None.
    """
    text = re.sub(r"&nbsp;", " ", tt_html)
    text = strip_tags(text)
    scores = re.findall(r"\d+\.\d+", text)
    return scores if len(scores) == 4 else None


def scrape_year(year: int) -> list[dict]:
    url = AFLTABLES_URL.format(year=year)
    print(f"  Fetching {url} ...", end=" ", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"ERROR: {e}")
        return []

    html = r.text
    print(f"{len(html):,} bytes")

    records = []

    # Find all <table> blocks that contain exactly 2 <tr> rows with <tt> score cells
    # These are the match tables
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL)
    tr_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
    tt_pattern = re.compile(r"<tt>(.*?)</tt>", re.DOTALL)

    for table_match in table_pattern.finditer(html):
        table_html = table_match.group(1)
        rows = tr_pattern.findall(table_html)

        if len(rows) != 2:
            continue

        # Both rows must have a <tt> score cell
        tt_row0 = tt_pattern.search(rows[0])
        tt_row1 = tt_pattern.search(rows[1])
        if not tt_row0 or not tt_row1:
            continue

        # Extract scores
        home_scores = extract_scores_from_tt(tt_row0.group(1))
        away_scores = extract_scores_from_tt(tt_row1.group(1))
        if home_scores is None or away_scores is None:
            continue

        # Extract team names from <a href="../teams/...">TeamName</a>
        team_link = re.compile(r'<a href="\.\./teams/[^"]+">([^<]+)</a>')
        home_team_match = team_link.search(rows[0])
        away_team_match = team_link.search(rows[1])
        if not home_team_match or not away_team_match:
            continue

        home_team = normalise_team(home_team_match.group(1))
        away_team = normalise_team(away_team_match.group(1))

        # Extract FT score (points) from the <td align=center> after <tt>
        ft_td = re.compile(r"<td[^>]*align=center[^>]*>\s*(\d+)\s*</td>")
        home_ft_match = ft_td.search(rows[0])
        away_ft_match = ft_td.search(rows[1])
        home_ft = int(home_ft_match.group(1)) if home_ft_match else None
        away_ft = int(away_ft_match.group(1)) if away_ft_match else None

        # Extract date from row 0 (home row has date/venue)
        date_match = re.search(r"(\d{1,2}-[A-Z][a-z]{2}-\d{4})", rows[0])
        if not date_match:
            continue
        game_date = parse_date(date_match.group(1))
        if not game_date:
            continue

        # Parse Q2 scores (index 1 = second quarter, cumulative)
        hg2, hb2, ht_home = parse_score_str(home_scores[1])
        ag2, ab2, ht_away = parse_score_str(away_scores[1])
        hg4, hb4, ft_home = parse_score_str(home_scores[3])
        ag4, ab4, ft_away = parse_score_str(away_scores[3])

        records.append({
            "year": year,
            "game_date": game_date,
            "home_team": home_team,
            "away_team": away_team,
            "ht_home_score":    ht_home,
            "ht_away_score":    ht_away,
            "ht_home_goals":    hg2,
            "ht_home_behinds":  hb2,
            "ht_away_goals":    ag2,
            "ht_away_behinds":  ab2,
            "ft_home_score_afl": home_ft if home_ft is not None else ft_home,
            "ft_away_score_afl": away_ft if away_ft is not None else ft_away,
        })

    print(f"    → {len(records)} games parsed")
    return records


def main(years: list[int]) -> None:
    all_records = []
    for year in years:
        records = scrape_year(year)
        all_records.extend(records)
        if year < years[-1]:
            time.sleep(1)

    if not all_records:
        print("No records scraped.")
        return

    scores_df = pd.DataFrame(all_records)

    # Deduplicate (afltables may have duplicates from nested tables)
    scores_df = scores_df.drop_duplicates(subset=["game_date", "home_team", "away_team"])
    HT_SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    scores_df.to_csv(HT_SCORES_PATH, index=False)
    print(f"\nRaw scores saved: {len(scores_df)} rows → {HT_SCORES_PATH}")

    # Show sample
    print(scores_df[["game_date","home_team","away_team","ht_home_score","ht_away_score"]].head(5).to_string(index=False))

    # Join to halftime dataset
    if not DATASET_PATH.exists():
        print(f"\nDataset not found at {DATASET_PATH} — skipping join")
        return

    dataset = pd.read_csv(DATASET_PATH)
    print(f"\nDataset loaded: {len(dataset)} rows")

    if "home_team" not in dataset.columns:
        print("Dataset missing home_team — columns:")
        print(dataset.columns.tolist())
        return

    # Dataset uses 'date' in DD/MM/YYYY format; scores_df uses 'game_date' in YYYY-MM-DD
    # Normalise both to YYYY-MM-DD for joining
    date_col = "date" if "date" in dataset.columns else "game_date"
    # Dataset has mixed formats: 'DD/MM/YYYY' (2022-25) and 'YYYY-MM-DD HH:MM:SS.mmm Z' (2026)
    # Parse each correctly: slash-format uses dayfirst; ISO format is unambiguous
    raw_dates = dataset[date_col].astype(str)
    def _norm_date(s: str) -> str:
        if "/" in s:
            return pd.to_datetime(s, dayfirst=True).strftime("%Y-%m-%d")
        return pd.to_datetime(s, utc=True).strftime("%Y-%m-%d")
    dataset["_join_date"] = raw_dates.apply(_norm_date)
    scores_df["_join_date"] = scores_df["game_date"]

    merge_cols = ["_join_date", "home_team", "away_team"]
    score_cols = [
        "ht_home_score", "ht_away_score",
        "ht_home_goals", "ht_home_behinds",
        "ht_away_goals", "ht_away_behinds",
        "ft_home_score_afl", "ft_away_score_afl",
    ]

    # Drop existing NA placeholder columns
    for col in score_cols + ["ht_score_diff", "ht_total_score", "ht_leader"]:
        if col in dataset.columns:
            dataset = dataset.drop(columns=[col])

    merged = dataset.merge(
        scores_df[merge_cols + score_cols],
        on=merge_cols,
        how="left",
    ).drop(columns=["_join_date"])

    filled = merged["ht_home_score"].notna().sum()
    total = len(merged)
    print(f"Matched: {filled}/{total} games ({100*filled/total:.1f}%)")

    # Derived columns
    merged["ht_score_diff"]  = merged["ht_home_score"] - merged["ht_away_score"]
    merged["ht_total_score"] = merged["ht_home_score"] + merged["ht_away_score"]
    merged["ht_leader"] = merged["ht_score_diff"].apply(
        lambda x: ("home" if x > 0 else ("away" if x < 0 else "level"))
        if pd.notna(x) else pd.NA
    )

    merged.to_csv(DATASET_PATH, index=False)
    print(f"Dataset updated → {DATASET_PATH}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--years", nargs="+", type=int, default=YEARS)
    args = p.parse_args()
    main(args.years)
