#!/usr/bin/env python3
"""
Scrape AFL game-level team statistics from AFL Tables.

The output is designed for post-game review, especially "unlucky loss" reads:
scoreboard result versus scoring shots, inside 50s, contested ball, clearances,
marks inside 50, and accuracy.

Outputs:
  outputs/afl_game_stats/afl_game_team_stats_2024_2025.csv
  outputs/afl_game_stats/afl_game_team_stats_2024_2025.jsonl
  outputs/afl_game_stats/afl_unlucky_losses_2024_2025.csv
  outputs/afl_game_stats/raw/{season}/{game_id}.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "afl_game_stats"
RAW_DIR = OUT_DIR / "raw"
CSV_PATH = OUT_DIR / "afl_game_team_stats_2024_2025.csv"
JSONL_PATH = OUT_DIR / "afl_game_team_stats_2024_2025.jsonl"
UNLUCKY_PATH = OUT_DIR / "afl_unlucky_losses_2024_2025.csv"

BASE = "https://afltables.com/afl/"
SEASON_URL = "https://afltables.com/afl/seas/{season}.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
}

TEAM_MAP = {
    "Adelaide": "Adelaide Crows",
    "Brisbane Lions": "Brisbane Lions",
    "Carlton": "Carlton Blues",
    "Collingwood": "Collingwood Magpies",
    "Essendon": "Essendon Bombers",
    "Fremantle": "Fremantle Dockers",
    "Geelong": "Geelong Cats",
    "Gold Coast": "Gold Coast Suns",
    "Greater Western Sydney": "Greater Western Sydney Giants",
    "GWS": "Greater Western Sydney Giants",
    "Hawthorn": "Hawthorn Hawks",
    "Melbourne": "Melbourne Demons",
    "North Melbourne": "North Melbourne Kangaroos",
    "Port Adelaide": "Port Adelaide Power",
    "Richmond": "Richmond Tigers",
    "St Kilda": "St Kilda Saints",
    "Sydney": "Sydney Swans",
    "West Coast": "West Coast Eagles",
    "Western Bulldogs": "Western Bulldogs",
}

STAT_MAP = {
    "KI": "kicks",
    "MK": "marks",
    "HB": "handballs",
    "DI": "disposals",
    "GL": "goals",
    "BH": "behinds",
    "HO": "hitouts",
    "TK": "tackles",
    "RB": "rebound_50s",
    "IF": "inside_50s",
    "CL": "clearances",
    "CG": "clangers",
    "FF": "frees_for",
    "FA": "frees_against",
    "BR": "brownlow_votes",
    "CP": "contested_possessions",
    "UP": "uncontested_possessions",
    "CM": "contested_marks",
    "MI": "marks_inside_50",
    "1%": "one_percenters",
    "BO": "bounces",
    "GA": "goal_assists",
}

FIELDNAMES = [
    "game_id",
    "season",
    "game_number",
    "round_label",
    "match_date",
    "venue",
    "attendance",
    "source_url",
    "team",
    "opponent",
    "team_side",
    "result",
    "points_for",
    "points_against",
    "margin",
    "goals",
    "behinds",
    "scoring_shots",
    "goal_accuracy",
    "opponent_goals",
    "opponent_behinds",
    "opponent_scoring_shots",
    "opponent_goal_accuracy",
    "shot_diff",
    "accuracy_diff",
    "kicks",
    "marks",
    "handballs",
    "disposals",
    "hitouts",
    "tackles",
    "rebound_50s",
    "inside_50s",
    "clearances",
    "clangers",
    "frees_for",
    "frees_against",
    "contested_possessions",
    "uncontested_possessions",
    "contested_marks",
    "marks_inside_50",
    "one_percenters",
    "bounces",
    "goal_assists",
    "inside_50_diff",
    "clearance_diff",
    "contested_possession_diff",
    "marks_inside_50_diff",
    "forward_efficiency",
    "opponent_forward_efficiency",
    "forward_efficiency_diff",
    "unlucky_loss_score",
    "unlucky_loss_flag",
]

log = logging.getLogger("afl_game_stats")


@dataclass
class TeamGame:
    game_id: str
    season: int
    game_number: int
    round_label: str
    match_date: str
    venue: str
    attendance: int | None
    source_url: str
    team: str
    opponent: str
    team_side: str
    result: str
    points_for: int
    points_against: int
    margin: int
    goals: int
    behinds: int
    scoring_shots: int
    goal_accuracy: float | None
    opponent_goals: int
    opponent_behinds: int
    opponent_scoring_shots: int
    opponent_goal_accuracy: float | None
    shot_diff: int
    accuracy_diff: float | None
    kicks: int
    marks: int
    handballs: int
    disposals: int
    hitouts: int
    tackles: int
    rebound_50s: int
    inside_50s: int
    clearances: int
    clangers: int
    frees_for: int
    frees_against: int
    contested_possessions: int
    uncontested_possessions: int
    contested_marks: int
    marks_inside_50: int
    one_percenters: int
    bounces: int
    goal_assists: int
    inside_50_diff: int
    clearance_diff: int
    contested_possession_diff: int
    marks_inside_50_diff: int
    forward_efficiency: float | None
    opponent_forward_efficiency: float | None
    forward_efficiency_diff: float | None
    unlucky_loss_score: int
    unlucky_loss_flag: int


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def to_int(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    value = clean(value).replace(",", "")
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def canon_team(team: str) -> str:
    team = clean(team)
    return TEAM_MAP.get(team, team)


def fetch_html(session: requests.Session, url: str) -> str:
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def get_game_urls(session: requests.Session, season: int) -> list[str]:
    soup = BeautifulSoup(fetch_html(session, SEASON_URL.format(season=season)), "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        if f"stats/games/{season}/" not in a["href"]:
            continue
        url = urljoin(BASE + "seas/", a["href"])
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def parse_header_table(table) -> dict[str, object]:
    text = table.get_text(" ", strip=True)
    round_label = re.search(r"Round:\s*([^ ]+(?: [^ ]+)?)\s+Venue:", text)
    venue = re.search(r"Venue:\s*(.*?)\s+Date:", text)
    date = re.search(r"Date:\s*(.*?)\s+Attendance:", text)
    attendance = re.search(r"Attendance:\s*([0-9,]+)", text)

    rows = []
    for tr in table.find_all("tr"):
        cells = [clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)

    score_rows = []
    for cells in rows:
        if len(cells) >= 5 and re.match(r"^\d+\.\d+\.\s+\d+$", cells[-1]):
            score_rows.append(cells)
    if len(score_rows) < 2:
        raise ValueError("Could not find two scoreboard rows")

    teams = []
    for cells in score_rows[:2]:
        team = canon_team(cells[0])
        final = cells[-1]
        m = re.match(r"^(\d+)\.(\d+)\.\s+(\d+)$", final)
        if not m:
            raise ValueError(f"Bad final score format: {final}")
        goals, behinds, points = map(int, m.groups())
        teams.append({"team": team, "goals": goals, "behinds": behinds, "points": points})

    return {
        "round_label": clean(round_label.group(1)) if round_label else "",
        "venue": clean(venue.group(1)) if venue else "",
        "match_date": clean(date.group(1)) if date else "",
        "attendance": to_int(attendance.group(1)) if attendance else None,
        "teams": teams,
    }


def parse_team_table(table) -> tuple[str, dict[str, int]]:
    title = clean(table.find("tr").get_text(" ", strip=True))
    team = canon_team(title.split(" Match Statistics", 1)[0])
    header = None
    totals = {field: 0 for field in STAT_MAP.values()}
    for tr in table.find_all("tr"):
        cells = [clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
        if len(cells) >= 4 and cells[0] == "#" and cells[1] == "Player":
            header = cells
            continue
        if not header or len(cells) != len(header):
            continue
        if cells[0] in ("", "#") or cells[1] in ("", "Player"):
            continue
        for idx, col in enumerate(header):
            field = STAT_MAP.get(col)
            if field:
                totals[field] += to_int(cells[idx])
    return team, totals


def pct(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def unlucky_score(row: dict[str, object]) -> int:
    if row["margin"] >= 0:
        return 0
    score = 0
    if row["shot_diff"] > 0:
        score += min(8, int(row["shot_diff"]))
    if row["inside_50_diff"] >= 8:
        score += 4
    elif row["inside_50_diff"] >= 4:
        score += 2
    if row["marks_inside_50_diff"] >= 3:
        score += 3
    if row["clearance_diff"] >= 5:
        score += 2
    if row["contested_possession_diff"] >= 10:
        score += 2
    if row["accuracy_diff"] is not None and row["accuracy_diff"] <= -0.10:
        score += 4
    if row["forward_efficiency_diff"] is not None and row["forward_efficiency_diff"] <= -0.08:
        score += 3
    if row["margin"] >= -12:
        score += 2
    elif row["margin"] >= -24:
        score += 1
    return score


def make_team_game(
    *,
    season: int,
    game_number: int,
    game_id: str,
    source_url: str,
    meta: dict[str, object],
    team_idx: int,
    team_stats: dict[str, int],
    opp_stats: dict[str, int],
) -> TeamGame:
    teams = meta["teams"]
    team_score = teams[team_idx]
    opp_score = teams[1 - team_idx]
    shots = team_score["goals"] + team_score["behinds"]
    opp_shots = opp_score["goals"] + opp_score["behinds"]
    points_for = team_score["points"]
    points_against = opp_score["points"]
    margin = points_for - points_against
    inside50 = team_stats["inside_50s"]
    opp_inside50 = opp_stats["inside_50s"]

    row = {
        "margin": margin,
        "shot_diff": shots - opp_shots,
        "inside_50_diff": inside50 - opp_inside50,
        "clearance_diff": team_stats["clearances"] - opp_stats["clearances"],
        "contested_possession_diff": team_stats["contested_possessions"] - opp_stats["contested_possessions"],
        "marks_inside_50_diff": team_stats["marks_inside_50"] - opp_stats["marks_inside_50"],
        "accuracy_diff": None,
        "forward_efficiency_diff": None,
    }
    acc = pct(team_score["goals"], shots)
    opp_acc = pct(opp_score["goals"], opp_shots)
    fwd_eff = pct(shots, inside50)
    opp_fwd_eff = pct(opp_shots, opp_inside50)
    row["accuracy_diff"] = round(acc - opp_acc, 4) if acc is not None and opp_acc is not None else None
    row["forward_efficiency_diff"] = (
        round(fwd_eff - opp_fwd_eff, 4) if fwd_eff is not None and opp_fwd_eff is not None else None
    )
    unlucky = unlucky_score(row)
    return TeamGame(
        game_id=game_id,
        season=season,
        game_number=game_number,
        round_label=str(meta["round_label"]),
        match_date=str(meta["match_date"]),
        venue=str(meta["venue"]),
        attendance=meta["attendance"],
        source_url=source_url,
        team=team_score["team"],
        opponent=opp_score["team"],
        team_side="team_a" if team_idx == 0 else "team_b",
        result="win" if margin > 0 else "loss" if margin < 0 else "draw",
        points_for=points_for,
        points_against=points_against,
        margin=margin,
        goals=team_score["goals"],
        behinds=team_score["behinds"],
        scoring_shots=shots,
        goal_accuracy=acc,
        opponent_goals=opp_score["goals"],
        opponent_behinds=opp_score["behinds"],
        opponent_scoring_shots=opp_shots,
        opponent_goal_accuracy=opp_acc,
        shot_diff=row["shot_diff"],
        accuracy_diff=row["accuracy_diff"],
        kicks=team_stats["kicks"],
        marks=team_stats["marks"],
        handballs=team_stats["handballs"],
        disposals=team_stats["disposals"],
        hitouts=team_stats["hitouts"],
        tackles=team_stats["tackles"],
        rebound_50s=team_stats["rebound_50s"],
        inside_50s=inside50,
        clearances=team_stats["clearances"],
        clangers=team_stats["clangers"],
        frees_for=team_stats["frees_for"],
        frees_against=team_stats["frees_against"],
        contested_possessions=team_stats["contested_possessions"],
        uncontested_possessions=team_stats["uncontested_possessions"],
        contested_marks=team_stats["contested_marks"],
        marks_inside_50=team_stats["marks_inside_50"],
        one_percenters=team_stats["one_percenters"],
        bounces=team_stats["bounces"],
        goal_assists=team_stats["goal_assists"],
        inside_50_diff=row["inside_50_diff"],
        clearance_diff=row["clearance_diff"],
        contested_possession_diff=row["contested_possession_diff"],
        marks_inside_50_diff=row["marks_inside_50_diff"],
        forward_efficiency=fwd_eff,
        opponent_forward_efficiency=opp_fwd_eff,
        forward_efficiency_diff=row["forward_efficiency_diff"],
        unlucky_loss_score=unlucky,
        unlucky_loss_flag=1 if unlucky >= 8 else 0,
    )


def parse_game(session: requests.Session, season: int, game_number: int, url: str) -> list[TeamGame]:
    html = fetch_html(session, url)
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    meta = parse_header_table(tables[0])
    stat_tables = []
    for table in tables:
        title = clean(table.find("tr").get_text(" ", strip=True)) if table.find("tr") else ""
        if " Match Statistics " in f" {title} ":
            stat_tables.append(table)
    if len(stat_tables) < 2:
        raise ValueError(f"Expected two stat tables, found {len(stat_tables)}")

    parsed = dict(parse_team_table(table) for table in stat_tables[:2])
    team_names = [t["team"] for t in meta["teams"]]
    if not all(team in parsed for team in team_names):
        raise ValueError(f"Score teams {team_names} did not match stat tables {sorted(parsed)}")

    game_id = Path(url).stem
    rows = [
        make_team_game(
            season=season,
            game_number=game_number,
            game_id=game_id,
            source_url=url,
            meta=meta,
            team_idx=0,
            team_stats=parsed[team_names[0]],
            opp_stats=parsed[team_names[1]],
        ),
        make_team_game(
            season=season,
            game_number=game_number,
            game_id=game_id,
            source_url=url,
            meta=meta,
            team_idx=1,
            team_stats=parsed[team_names[1]],
            opp_stats=parsed[team_names[0]],
        ),
    ]

    raw_dir = RAW_DIR / str(season)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{game_id}.json").write_text(
        json.dumps({"source_url": url, "teams": [asdict(row) for row in rows]}, indent=2),
        encoding="utf-8",
    )
    return rows


def write_outputs(rows: list[TeamGame]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dict_rows = [asdict(row) for row in rows]

    existing: dict[tuple[int, str, str], dict] = {}
    if CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                key = (int(row["season"]), row["game_id"], row["team_side"])
                existing[key] = row

    for row in dict_rows:
        key = (int(row["season"]), row["game_id"], row["team_side"])
        existing[key] = row

    combined = sorted(
        existing.values(),
        key=lambda r: (
            int(r["season"]),
            int(r["game_number"]),
            r["game_id"],
            r["team_side"],
        ),
    )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(combined)
    with JSONL_PATH.open("w", encoding="utf-8") as fh:
        for row in combined:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    unlucky = [row for row in combined if row["unlucky_loss_flag"]]
    with UNLUCKY_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unlucky)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape AFL game-level team stats from AFL Tables.")
    parser.add_argument("--seasons", nargs="+", type=int, default=[2024, 2025])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)

    session = requests.Session()
    all_rows: list[TeamGame] = []
    for season in args.seasons:
        urls = get_game_urls(session, season)
        if args.limit:
            urls = urls[: args.limit]
        log.info("%s: %d game stat URLs", season, len(urls))
        for idx, url in enumerate(urls, 1):
            rows = parse_game(session, season, idx, url)
            all_rows.extend(rows)
            if idx % 25 == 0:
                write_outputs(all_rows)
                log.info("Checkpoint %s: %d games, %d team rows", season, idx, len(all_rows))
            time.sleep(args.pause)

    write_outputs(all_rows)
    games = {(row.season, row.game_id) for row in all_rows}
    log.info("Wrote %s", CSV_PATH)
    log.info("Wrote %s", JSONL_PATH)
    log.info("Wrote %s", UNLUCKY_PATH)
    log.info("Scraped %d games, %d team rows", len(games), len(all_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
