#!/usr/bin/env python3
"""
Find AFL game report/article records for 2024 and 2025.

Inputs:
  outputs/afl_game_stats/afl_game_team_stats_2024_2025.csv

Outputs:
  outputs/afl_game_reports/afl_game_reports_2024_2025.csv
  outputs/afl_game_reports/afl_game_reports_2024_2025.jsonl
  outputs/afl_game_reports/afl_game_reports_2024_2025_unmatched.csv

Source slots:
  - fox: Fox Sports AFL article/live blog/news-story discovered via daily sitemaps.
  - secondary: AFL.com.au official match centre from the public AFL API.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
STATS_CSV = ROOT / "outputs" / "afl_game_stats" / "afl_game_team_stats_2024_2025.csv"
OUT_DIR = ROOT / "outputs" / "afl_game_reports"
CSV_PATH = OUT_DIR / "afl_game_reports_2024_2025.csv"
JSONL_PATH = OUT_DIR / "afl_game_reports_2024_2025.jsonl"
UNMATCHED_PATH = OUT_DIR / "afl_game_reports_2024_2025_unmatched.csv"

FOX_DAILY_SITEMAP = "https://www.foxsports.com.au/sitemap.xml?yyyy={yyyy}&mm={mm}&dd={dd}"
AFL_MATCHES_API = "https://aflapi.afl.com.au/afl/v2/matches?compSeasonId={comp_season_id}&pageSize=250"
AFL_MATCH_URL = "https://www.afl.com.au/afl/matches/{match_id}"
COMP_SEASON_IDS = {2024: 62, 2025: 73}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml,application/json,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

TEAM_ALIASES = {
    "Adelaide Crows": ("adelaide", "crows"),
    "Brisbane Lions": ("brisbane", "lions"),
    "Carlton Blues": ("carlton", "blues"),
    "Collingwood Magpies": ("collingwood", "magpies", "pies"),
    "Essendon Bombers": ("essendon", "bombers"),
    "Fremantle Dockers": ("fremantle", "dockers"),
    "Geelong Cats": ("geelong", "cats"),
    "Gold Coast Suns": ("gold coast", "suns"),
    "Greater Western Sydney Giants": ("greater western sydney", "gws", "giants"),
    "Hawthorn Hawks": ("hawthorn", "hawks"),
    "Melbourne Demons": ("melbourne", "demons", "dees"),
    "North Melbourne Kangaroos": ("north melbourne", "kangaroos", "roos"),
    "Port Adelaide Power": ("port adelaide", "power"),
    "Richmond Tigers": ("richmond", "tigers"),
    "St Kilda Saints": ("st kilda", "saints"),
    "Sydney Swans": ("sydney", "swans"),
    "West Coast Eagles": ("west coast", "eagles"),
    "Western Bulldogs": ("western bulldogs", "bulldogs"),
}

AFL_API_TEAM_MAP = {
    "Adelaide Crows": "Adelaide Crows",
    "Melbourne": "Melbourne Demons",
    "North Melbourne": "North Melbourne Kangaroos",
    "Port Adelaide": "Port Adelaide Power",
    "St Kilda": "St Kilda Saints",
    "Gold Coast SUNS": "Gold Coast Suns",
    "GWS Giants": "Greater Western Sydney Giants",
    "GWS GIANTS": "Greater Western Sydney Giants",
    "Carlton": "Carlton Blues",
    "Collingwood": "Collingwood Magpies",
    "Essendon": "Essendon Bombers",
    "Fremantle": "Fremantle Dockers",
    "Hawthorn": "Hawthorn Hawks",
    "Richmond": "Richmond Tigers",
    "West Coast Eagles": "West Coast Eagles",
    "Western Bulldogs": "Western Bulldogs",
}

BAD_FOX_PARTS = (
    "supercoach",
    "fantasy",
    "teams",
    "team-news",
    "injury",
    "tribunal",
    "trade",
    "draft",
    "power-rankings",
    "predicted",
    "tips",
    "preview",
    "what-time",
    "fixture",
    "ladder",
)

log = logging.getLogger("afl_game_reports")
FOX_SITEMAP_CACHE: dict[str, list[str]] = {}


@dataclass
class Game:
    game_id: str
    season: int
    game_number: int
    match_date_iso: str
    match_date_raw: str
    round_label: str
    venue: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    afl_match_id: int | None = None
    afl_match_url: str = ""


@dataclass
class Report:
    report_id: str
    game_id: str
    season: int
    game_number: int
    match_date: str
    round_label: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    source_slot: str
    source: str
    title: str
    url: str
    published: str
    description: str
    excerpt: str
    match_method: str
    match_rank: int


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def to_iso_date(raw: str) -> str:
    raw = clean(raw)
    raw = re.sub(r"\s+\([^)]*\)$", "", raw)
    for fmt in ("%a, %d-%b-%Y %I:%M %p", "%a, %d-%b-%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def canon_api_team(raw: str) -> str:
    raw = clean(raw)
    return AFL_API_TEAM_MAP.get(raw, raw)


def source_name(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if "foxsports.com.au" in host:
        return "Fox Sports"
    if "afl.com.au" in host:
        return "AFL.com.au"
    return host


def slug_text(url: str) -> str:
    path = urlparse(url).path.lower()
    path = re.sub(r"/news-story/[a-f0-9]+.*$", "", path)
    path = re.sub(r"/news/\d+/", " ", path)
    return clean(path.replace("/", " ").replace("-", " "))


def scoreline(game: Game) -> str:
    return f"{game.home_score}-{game.away_score}"


def load_games() -> list[Game]:
    rows = list(csv.DictReader(STATS_CSV.open(encoding="utf-8")))
    by_game: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_game.setdefault(f"{row['season']}:{row['game_id']}", []).append(row)

    games: list[Game] = []
    for game_rows in by_game.values():
        pair = sorted(game_rows, key=lambda r: r["team_side"])
        if len(pair) != 2:
            continue
        a, b = pair
        games.append(
            Game(
                game_id=a["game_id"],
                season=int(a["season"]),
                game_number=int(a["game_number"]),
                match_date_iso=to_iso_date(a["match_date"]),
                match_date_raw=a["match_date"],
                round_label=a["round_label"],
                venue=a["venue"],
                home_team=a["team"],
                away_team=b["team"],
                home_score=int(a["points_for"]),
                away_score=int(b["points_for"]),
            )
        )
    games.sort(key=lambda g: (g.season, g.game_number))
    return games


def fetch_afl_matches(session: requests.Session, season: int) -> list[dict]:
    url = AFL_MATCHES_API.format(comp_season_id=COMP_SEASON_IDS[season])
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json().get("matches", [])


def attach_afl_match_ids(session: requests.Session, games: list[Game]) -> None:
    api_games: list[dict] = []
    for season in sorted({g.season for g in games}):
        api_games.extend(fetch_afl_matches(session, season))
        time.sleep(0.1)

    index: dict[tuple[object, ...], dict] = {}
    for m in api_games:
        season = int(m["compSeason"]["providerId"][4:8])
        day = datetime.strptime(m["utcStartTime"][:10], "%Y-%m-%d").date().isoformat()
        home = canon_api_team(m["home"]["team"]["name"])
        away = canon_api_team(m["away"]["team"]["name"])
        hs = int(m["home"]["score"]["totalScore"])
        away_score = int(m["away"]["score"]["totalScore"])
        index[(season, day, home, away, hs, away_score)] = m

    matched = 0
    for game in games:
        key = (game.season, game.match_date_iso, game.home_team, game.away_team, game.home_score, game.away_score)
        match = index.get(key)
        if not match:
            continue
        game.afl_match_id = int(match["id"])
        game.afl_match_url = AFL_MATCH_URL.format(match_id=game.afl_match_id)
        matched += 1
    log.info("Matched %d/%d games to AFL.com.au match IDs", matched, len(games))


def game_dates(game: Game) -> list[date]:
    try:
        base = datetime.strptime(game.match_date_iso, "%Y-%m-%d").date()
    except ValueError:
        return []
    return [base + timedelta(days=offset) for offset in (-1, 0, 1, 2)]


def fox_sitemap_urls(session: requests.Session, day: date) -> list[str]:
    key = day.isoformat()
    if key in FOX_SITEMAP_CACHE:
        return FOX_SITEMAP_CACHE[key]
    url = FOX_DAILY_SITEMAP.format(yyyy=day.year, mm=f"{day.month:02d}", dd=f"{day.day:02d}")
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            FOX_SITEMAP_CACHE[key] = []
            return []
    except Exception:
        FOX_SITEMAP_CACHE[key] = []
        return []
    urls = [
        html.unescape(loc)
        for loc in re.findall(r"<loc>(.*?)</loc>", resp.text)
        if "/afl/" in loc and "/news-story/" in loc
    ]
    FOX_SITEMAP_CACHE[key] = urls
    time.sleep(0.05)
    return urls


def fox_candidates(session: requests.Session, game: Game) -> list[dict[str, str]]:
    seen: set[str] = set()
    candidates = []
    for day in game_dates(game):
        for url in fox_sitemap_urls(session, day):
            if url in seen:
                continue
            seen.add(url)
            text = slug_text(url)
            candidates.append({"title": text, "url": url, "snippet": text})
    return candidates


def fox_score(game: Game, candidate: dict[str, str]) -> int:
    url = candidate["url"].lower()
    haystack = f"{candidate['title']} {candidate['snippet']} {url}".lower()
    if any(part in haystack for part in BAD_FOX_PARTS):
        return -5
    matched_teams = 0
    for team in (game.home_team, game.away_team):
        if any(alias in haystack for alias in TEAM_ALIASES.get(team, ())):
            matched_teams += 1
    exact_score = scoreline(game) in haystack or scoreline(game).replace("-", " ") in haystack
    if matched_teams < 2 and not exact_score:
        return -10
    score = matched_teams * 8
    if str(game.season) in haystack:
        score += 3
    if exact_score:
        score += 8
    if any(term in haystack for term in ("live score", "live-score", "result", "match report", "highlights", "defeat", "defeats", "beat")):
        score += 8
    return score


def select_fox(game: Game, candidates: list[dict[str, str]]) -> tuple[dict[str, str] | None, int]:
    ranked = sorted(
        ((fox_score(game, cand), idx + 1, cand) for idx, cand in enumerate(candidates)),
        key=lambda x: (x[0], -x[1]),
        reverse=True,
    )
    for score, rank, cand in ranked:
        if score >= 14:
            return cand, rank
    return None, 0


def extract_article(session: requests.Session, url: str) -> dict[str, str]:
    data = {"title": "", "published": "", "description": "", "excerpt": ""}
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        if resp.status_code >= 400:
            return data
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return data

    if soup.title:
        data["title"] = clean(soup.title.get_text(" ", strip=True))
    for meta_name, key in (
        ("og:title", "title"),
        ("article:published_time", "published"),
        ("og:description", "description"),
        ("description", "description"),
    ):
        if meta_name.startswith("og:") or meta_name.startswith("article:"):
            meta = soup.find("meta", property=meta_name)
        else:
            meta = soup.find("meta", attrs={"name": meta_name})
        if meta and meta.get("content") and not data[key]:
            data[key] = clean(meta["content"])

    paragraphs = []
    for p in soup.find_all("p"):
        text = clean(p.get_text(" ", strip=True))
        if len(text) < 40:
            continue
        if any(skip in text.lower() for skip in ("subscribe", "sign up", "cookies", "advertisement")):
            continue
        paragraphs.append(text)
        if sum(len(x) for x in paragraphs) > 1400:
            break
    data["excerpt"] = clean(" ".join(paragraphs))[:1200]
    return data


def report_id(game: Game, slot: str, url: str) -> str:
    raw = f"{game.season}:{game.game_id}:{slot}:{url}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def make_report(game: Game, slot: str, url: str, rank: int, method: str, article: dict[str, str]) -> Report:
    title = article["title"] or slug_text(url)
    return Report(
        report_id=report_id(game, slot, url),
        game_id=game.game_id,
        season=game.season,
        game_number=game.game_number,
        match_date=game.match_date_iso,
        round_label=game.round_label,
        home_team=game.home_team,
        away_team=game.away_team,
        home_score=game.home_score,
        away_score=game.away_score,
        source_slot=slot,
        source=source_name(url),
        title=title,
        url=url,
        published=article["published"],
        description=article["description"],
        excerpt=article["excerpt"],
        match_method=method,
        match_rank=rank,
    )


def write_outputs(reports: list[Report], unmatched: list[dict[str, object]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = list(Report.__dataclass_fields__)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for report in reports:
            writer.writerow(asdict(report))
    with JSONL_PATH.open("w", encoding="utf-8") as fh:
        for report in reports:
            fh.write(json.dumps(asdict(report), ensure_ascii=False) + "\n")
    unmatched_fields = [
        "game_id",
        "season",
        "game_number",
        "match_date",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "source_slot",
        "reason",
    ]
    with UNMATCHED_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=unmatched_fields)
        writer.writeheader()
        writer.writerows(unmatched)


def unmatched_row(game: Game, slot: str, reason: str) -> dict[str, object]:
    return {
        "game_id": game.game_id,
        "season": game.season,
        "game_number": game.game_number,
        "match_date": game.match_date_iso,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "home_score": game.home_score,
        "away_score": game.away_score,
        "source_slot": slot,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape AFL game report metadata.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--pause", type=float, default=0.1)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)

    session = requests.Session()
    games = load_games()
    if args.limit:
        games = games[: args.limit]
    attach_afl_match_ids(session, games)

    reports: list[Report] = []
    unmatched: list[dict[str, object]] = []
    for idx, game in enumerate(games, 1):
        selected, rank = select_fox(game, fox_candidates(session, game))
        if selected:
            reports.append(make_report(game, "fox", selected["url"], rank, "fox_daily_sitemap", extract_article(session, selected["url"])))
        else:
            unmatched.append(unmatched_row(game, "fox", "no Fox sitemap candidate above threshold"))

        if game.afl_match_url:
            reports.append(make_report(game, "secondary", game.afl_match_url, 1, "afl_api_match_centre", extract_article(session, game.afl_match_url)))
        else:
            unmatched.append(unmatched_row(game, "secondary", "no AFL.com.au match id matched"))

        if idx % 25 == 0:
            write_outputs(reports, unmatched)
            log.info("Checkpoint: %d/%d games, %d reports", idx, len(games), len(reports))
        time.sleep(args.pause)

    write_outputs(reports, unmatched)
    log.info("Wrote %s", CSV_PATH)
    log.info("Wrote %s", JSONL_PATH)
    log.info("Wrote %s", UNMATCHED_PATH)
    log.info("Matched %d/%d source slots", len(reports), len(games) * 2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
