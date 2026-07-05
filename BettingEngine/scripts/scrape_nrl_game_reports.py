#!/usr/bin/env python3
"""
Find two written report-style articles for NRL games.

Outputs:
  outputs/nrl_game_reports/nrl_game_reports_2024_2025.csv
  outputs/nrl_game_reports/nrl_game_reports_2024_2025.jsonl
  outputs/nrl_game_reports/nrl_game_reports_2024_2025_unmatched.csv

The first target source is Fox Sports. The second target source is a reputable
non-Fox source, preferring NRL.com and then major Australian/sports outlets.
The script stores metadata and short excerpts, not full article bodies.
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
from typing import Iterable
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "nrl_game_reports"
CSV_PATH = OUT_DIR / "nrl_game_reports_2024_2025.csv"
JSONL_PATH = OUT_DIR / "nrl_game_reports_2024_2025.jsonl"
UNMATCHED_PATH = OUT_DIR / "nrl_game_reports_2024_2025_unmatched.csv"

NRL_DRAW_API = "https://www.nrl.com/draw/data/?competition=111&season={season}&round={round}"
DDG_HTML = "https://html.duckduckgo.com/html/?q={query}"
FOX_DAILY_SITEMAP = "https://www.foxsports.com.au/sitemap.xml?yyyy={yyyy}&mm={mm}&dd={dd}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

TEAM_CANON = {
    "Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Canterbury Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Cowboys": "North Queensland Cowboys",
    "Dragons": "St. George Illawarra Dragons",
    "Eels": "Parramatta Eels",
    "Knights": "Newcastle Knights",
    "Panthers": "Penrith Panthers",
    "Rabbitohs": "South Sydney Rabbitohs",
    "Raiders": "Canberra Raiders",
    "Roosters": "Sydney Roosters",
    "Sea Eagles": "Manly-Warringah Sea Eagles",
    "Sharks": "Cronulla-Sutherland Sharks",
    "Storm": "Melbourne Storm",
    "Titans": "Gold Coast Titans",
    "Warriors": "New Zealand Warriors",
    "Wests Tigers": "Wests Tigers",
    "Broncos": "Brisbane Broncos",
    "Dolphins": "Dolphins",
}

TEAM_ALIASES = {
    "Brisbane Broncos": ("brisbane", "broncos"),
    "Canberra Raiders": ("canberra", "raiders"),
    "Canterbury-Bankstown Bulldogs": ("canterbury", "bulldogs"),
    "Cronulla-Sutherland Sharks": ("cronulla", "sharks"),
    "Dolphins": ("dolphins",),
    "Gold Coast Titans": ("gold coast", "titans"),
    "Manly-Warringah Sea Eagles": ("manly", "sea eagles", "eagles"),
    "Melbourne Storm": ("melbourne", "storm"),
    "New Zealand Warriors": ("new zealand", "nz warriors", "warriors"),
    "Newcastle Knights": ("newcastle", "knights"),
    "North Queensland Cowboys": ("north queensland", "cowboys"),
    "Parramatta Eels": ("parramatta", "eels"),
    "Penrith Panthers": ("penrith", "panthers"),
    "South Sydney Rabbitohs": ("south sydney", "rabbitohs"),
    "St. George Illawarra Dragons": ("st george", "dragons"),
    "Sydney Roosters": ("sydney roosters", "roosters"),
    "Wests Tigers": ("wests tigers", "tigers"),
}

SECONDARY_DOMAINS = (
    "nrl.com",
    "abc.net.au",
    "espn.com.au",
    "nine.com.au",
    "wwos.nine.com.au",
    "sportingnews.com",
    "zerotackle.com",
    "theguardian.com",
)

BAD_URL_PARTS = (
    "/watch/",
    "video",
    "highlights",
    "press-conference",
    "team-list",
    "late-mail",
    "predicted",
    "preview",
    "tips",
    "supercoach",
    "odds",
    "ladder",
    "talking-points",
    "late-mail",
    "casualty-ward",
    "transfer-centre",
    "what-time",
    "how-america",
    "american-reaction",
    "racial",
    "judiciary",
    "suspension",
    "press-conference",
)

log = logging.getLogger("nrl_game_reports")
FOX_SITEMAP_CACHE: dict[str, list[str]] = {}


@dataclass
class Game:
    season: int
    round_number: int
    game_number: int
    match_date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    venue: str
    nrl_match_centre_url: str
    nrl_highlights_url: str


@dataclass
class Report:
    report_id: str
    season: int
    round_number: int
    game_number: int
    match_date: str
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
    search_query: str
    search_rank: int


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def canon_team(name: str) -> str:
    return TEAM_CANON.get(clean_text(name), clean_text(name))


def scoreline(game: Game) -> str:
    return f"{game.home_score}-{game.away_score}"


def source_name(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if "foxsports.com.au" in host:
        return "Fox Sports"
    if host.endswith("nrl.com"):
        return "NRL.com"
    if "abc.net.au" in host:
        return "ABC"
    if "espn" in host:
        return "ESPN"
    if "nine.com.au" in host:
        return "Nine"
    if "sportingnews.com" in host:
        return "Sporting News"
    if "zerotackle.com" in host:
        return "Zero Tackle"
    if "theguardian.com" in host:
        return "The Guardian"
    return host


def normalise_ddg_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)
    return url


def slug_text(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.lower()
    path = re.sub(r"/news-story/[a-f0-9]+.*$", "", path)
    path = path.replace("/", " ").replace("-", " ")
    return clean_text(path)


def game_dates(game: Game) -> list[date]:
    try:
        base = datetime.strptime(game.match_date, "%Y-%m-%d").date()
    except ValueError:
        return []
    return [base + timedelta(days=offset) for offset in (-1, 0, 1, 2)]


def get_json(session: requests.Session, url: str) -> dict | None:
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            log.debug("GET %s -> HTTP %s", url, resp.status_code)
            return None
        return resp.json()
    except Exception as exc:
        log.debug("GET %s failed: %s", url, exc)
        return None


def build_games(session: requests.Session, seasons: Iterable[int]) -> list[Game]:
    games: list[Game] = []
    seen_games: set[tuple[object, ...]] = set()
    for season in seasons:
        for round_number in range(1, 33):
            raw = get_json(session, NRL_DRAW_API.format(season=season, round=round_number))
            if not raw:
                continue
            game_number = 0
            for fixture in raw.get("fixtures", []):
                if fixture.get("type") != "Match" or fixture.get("matchState") != "FullTime":
                    continue
                home = fixture.get("homeTeam", {})
                away = fixture.get("awayTeam", {})
                if home.get("score") is None or away.get("score") is None:
                    continue
                game_number += 1
                kickoff = fixture.get("clock", {}).get("kickOffTimeLong") or ""
                game = Game(
                    season=season,
                    round_number=round_number,
                    game_number=game_number,
                    match_date=kickoff[:10],
                    home_team=canon_team(home.get("nickName", "")),
                    away_team=canon_team(away.get("nickName", "")),
                    home_score=int(home.get("score")),
                    away_score=int(away.get("score")),
                    venue=clean_text(fixture.get("venue", "")),
                    nrl_match_centre_url=urljoin("https://www.nrl.com", fixture.get("matchCentreUrl", "")),
                    nrl_highlights_url=fixture.get("callToAction", {}).get("url", ""),
                )
                dedupe_key = (
                    game.season,
                    game.match_date,
                    game.home_team,
                    game.away_team,
                    game.home_score,
                    game.away_score,
                )
                if dedupe_key in seen_games:
                    continue
                seen_games.add(dedupe_key)
                games.append(game)
            time.sleep(0.15)
    return games


def ddg_search(session: requests.Session, query: str, pause: float) -> list[dict[str, str]]:
    url = DDG_HTML.format(query=quote(query))
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            log.debug("DDG HTTP %s for %s", resp.status_code, query)
            return []
    except Exception as exc:
        log.debug("DDG failed for %s: %s", query, exc)
        return []
    finally:
        time.sleep(pause)

    soup = BeautifulSoup(resp.text, "html.parser")
    results: list[dict[str, str]] = []
    for result in soup.select(".result"):
        a = result.select_one(".result__a")
        if not a:
            continue
        href = normalise_ddg_url(a.get("href", ""))
        if not href.startswith("http"):
            continue
        snippet_el = result.select_one(".result__snippet")
        results.append(
            {
                "title": clean_text(a.get_text(" ", strip=True)),
                "url": href,
                "snippet": clean_text(snippet_el.get_text(" ", strip=True) if snippet_el else ""),
            }
        )
    return results


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
        if "/nrl/" in loc and "/news-story/" in loc
    ]
    FOX_SITEMAP_CACHE[key] = urls
    time.sleep(0.1)
    return urls


def sitemap_candidates(session: requests.Session, game: Game, slot: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    if slot == "fox":
        seen: set[str] = set()
        for day in game_dates(game):
            for url in fox_sitemap_urls(session, day):
                if url in seen:
                    continue
                seen.add(url)
                candidates.append({"title": slug_text(url), "url": url, "snippet": slug_text(url)})
        return candidates

    if game.nrl_highlights_url:
        candidates.append(
            {
                "title": slug_text(game.nrl_highlights_url),
                "url": game.nrl_highlights_url,
                "snippet": "Official NRL.com match content linked from the draw API.",
            }
        )
    if game.nrl_match_centre_url:
        candidates.append(
            {
                "title": slug_text(game.nrl_match_centre_url),
                "url": game.nrl_match_centre_url,
                "snippet": "Official NRL.com match centre.",
            }
        )
    return candidates


def is_bad_candidate(url: str, title: str) -> bool:
    haystack = f"{url} {title}".lower()
    return any(part in haystack for part in BAD_URL_PARTS)


def candidate_score(game: Game, candidate: dict[str, str], slot: str) -> int:
    url = candidate["url"].lower()
    title = candidate["title"].lower()
    snippet = candidate["snippet"].lower()
    haystack = f"{url} {title} {snippet}"
    if slot == "fox" and "foxsports.com.au" not in url:
        return -100
    if slot == "secondary":
        if "foxsports.com.au" in url:
            return -100
        if not any(domain in url for domain in SECONDARY_DOMAINS):
            return -50
    if slot == "fox" and is_bad_candidate(url, title):
        return -15

    score = 0
    matched_teams = 0
    for team in (game.home_team, game.away_team):
        aliases = TEAM_ALIASES.get(team, tuple(p.lower() for p in re.split(r"[\s.-]+", team) if len(p) > 3))
        if any(alias in haystack for alias in aliases):
            matched_teams += 1
            score += 8
    exact_scoreline = scoreline(game) in haystack or scoreline(game).replace("-", " ") in haystack
    if slot == "fox" and matched_teams < 2 and not exact_scoreline:
        return -10
    if str(game.season) in haystack:
        score += 4
    if f"round {game.round_number}" in haystack or f"round-{game.round_number}" in haystack:
        score += 4
    if exact_scoreline:
        score += 8
    if slot == "fox" and any(term in haystack for term in ("live score", "live-score", "live scores", "live-scores", "updates", "scores stats", "scores-stats")):
        score += 14
    if any(word in haystack for word in ("defeat", "beats", "beat", "down", "win", "loss", "live", "blog", "result")):
        score += 3
    if "news-story" in url:
        score += 3
    if slot == "secondary" and "nrl.com" in url:
        score += 10
    return score


def make_queries(game: Game, slot: str) -> list[str]:
    teams = f'"{game.home_team}" "{game.away_team}"'
    reverse = f'"{game.away_team}" "{game.home_team}"'
    points = f'"{scoreline(game)}"'
    base = f'{teams} {points} "Round {game.round_number}" {game.season} NRL report'
    if slot == "fox":
        return [
            f"site:foxsports.com.au/nrl/nrl-premiership {base}",
            f"site:foxsports.com.au/nrl/nrl-premiership {reverse} {points} {game.season} NRL result",
        ]
    return [
        f"site:nrl.com/news {base}",
        f'{base} -site:foxsports.com.au',
        f'{reverse} {points} {game.season} NRL match report -site:foxsports.com.au',
    ]


def select_candidate(game: Game, slot: str, candidates: list[dict[str, str]]) -> tuple[dict[str, str] | None, int]:
    ranked = sorted(
        ((candidate_score(game, candidate, slot), index + 1, candidate) for index, candidate in enumerate(candidates)),
        key=lambda item: (item[0], -item[1]),
        reverse=True,
    )
    for score, rank, candidate in ranked:
        threshold = 8 if slot == "fox" else 6
        if score >= threshold:
            return candidate, rank
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
        data["title"] = clean_text(soup.title.get_text(" ", strip=True))
    for meta_name, key in (
        ("og:title", "title"),
        ("article:published_time", "published"),
        ("pubdate", "published"),
        ("og:description", "description"),
        ("description", "description"),
    ):
        if meta_name.startswith("og:") or meta_name.startswith("article:"):
            meta = soup.find("meta", property=meta_name)
        else:
            meta = soup.find("meta", attrs={"name": meta_name})
        if meta and meta.get("content") and not data[key]:
            data[key] = clean_text(meta["content"])

    paragraphs = []
    for p in soup.find_all("p"):
        text = clean_text(p.get_text(" ", strip=True))
        if len(text) < 40:
            continue
        if any(skip in text.lower() for skip in ("subscribe", "sign up", "cookies", "advertisement")):
            continue
        paragraphs.append(text)
        if sum(len(x) for x in paragraphs) > 1400:
            break
    data["excerpt"] = clean_text(" ".join(paragraphs))[:1200]
    return data


def report_id(game: Game, slot: str, url: str) -> str:
    raw = f"{game.season}:{game.round_number}:{game.game_number}:{slot}:{url}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def find_report(session: requests.Session, game: Game, slot: str, pause: float) -> tuple[Report | None, str]:
    seen: set[str] = set()
    all_candidates: list[dict[str, str]] = sitemap_candidates(session, game, slot)
    used_query = ""
    selected, rank = select_candidate(game, slot, all_candidates)
    if selected:
        article = extract_article(session, selected["url"])
        title = article["title"] or selected["title"]
        description = article["description"] or selected["snippet"]
        return (
            Report(
                report_id=report_id(game, slot, selected["url"]),
                season=game.season,
                round_number=game.round_number,
                game_number=game.game_number,
                match_date=game.match_date,
                home_team=game.home_team,
                away_team=game.away_team,
                home_score=game.home_score,
                away_score=game.away_score,
                source_slot=slot,
                source=source_name(selected["url"]),
                title=title,
                url=selected["url"],
                published=article["published"],
                description=description,
                excerpt=article["excerpt"],
                search_query="sitemap/direct",
                search_rank=rank,
            ),
            "",
        )

    for query in make_queries(game, slot):
        used_query = query
        for candidate in ddg_search(session, query, pause):
            if candidate["url"] in seen:
                continue
            seen.add(candidate["url"])
            all_candidates.append(candidate)
        selected, rank = select_candidate(game, slot, all_candidates)
        if selected:
            article = extract_article(session, selected["url"])
            title = article["title"] or selected["title"]
            description = article["description"] or selected["snippet"]
            return (
                Report(
                    report_id=report_id(game, slot, selected["url"]),
                    season=game.season,
                    round_number=game.round_number,
                    game_number=game.game_number,
                    match_date=game.match_date,
                    home_team=game.home_team,
                    away_team=game.away_team,
                    home_score=game.home_score,
                    away_score=game.away_score,
                    source_slot=slot,
                    source=source_name(selected["url"]),
                    title=title,
                    url=selected["url"],
                    published=article["published"],
                    description=description,
                    excerpt=article["excerpt"],
                    search_query=used_query,
                    search_rank=rank,
                ),
                "",
            )
    return None, used_query


def write_outputs(reports: list[Report], unmatched: list[dict[str, object]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(reports[0]).keys()) if reports else list(Report.__dataclass_fields__)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for report in reports:
            writer.writerow(asdict(report))
    with JSONL_PATH.open("w", encoding="utf-8") as fh:
        for report in reports:
            fh.write(json.dumps(asdict(report), ensure_ascii=False) + "\n")
    with UNMATCHED_PATH.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "season",
            "round_number",
            "game_number",
            "match_date",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "source_slot",
            "last_query",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in unmatched:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape NRL 2024/2025 game report metadata.")
    parser.add_argument("--seasons", nargs="+", type=int, default=[2024, 2025])
    parser.add_argument("--limit", type=int, default=0, help="Limit games for test runs.")
    parser.add_argument("--pause", type=float, default=1.2, help="Pause after each search request.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)
    session = requests.Session()
    games = build_games(session, args.seasons)
    games.sort(key=lambda g: (g.season, g.round_number, g.game_number))
    if args.limit:
        games = games[: args.limit]
    log.info("Loaded %d games", len(games))

    reports: list[Report] = []
    unmatched: list[dict[str, object]] = []
    total_slots = len(games) * 2
    done_slots = 0
    for game in games:
        log.info(
            "%s R%s G%s: %s %s-%s %s",
            game.season,
            game.round_number,
            game.game_number,
            game.home_team,
            game.home_score,
            game.away_score,
            game.away_team,
        )
        for slot in ("fox", "secondary"):
            report, last_query = find_report(session, game, slot, args.pause)
            done_slots += 1
            if report:
                reports.append(report)
                log.info("  %s: %s | %s", slot, report.source, report.title[:90])
            else:
                unmatched.append(
                    {
                        "season": game.season,
                        "round_number": game.round_number,
                        "game_number": game.game_number,
                        "match_date": game.match_date,
                        "home_team": game.home_team,
                        "away_team": game.away_team,
                        "home_score": game.home_score,
                        "away_score": game.away_score,
                        "source_slot": slot,
                        "last_query": last_query,
                    }
                )
                log.warning("  %s: no candidate", slot)
            if done_slots % 20 == 0:
                write_outputs(reports, unmatched)
                log.info("Checkpoint: %d/%d slots, %d reports", done_slots, total_slots, len(reports))

    write_outputs(reports, unmatched)
    log.info("Wrote %s", CSV_PATH)
    log.info("Wrote %s", JSONL_PATH)
    log.info("Wrote %s", UNMATCHED_PATH)
    log.info("Matched %d/%d report slots", len(reports), total_slots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
