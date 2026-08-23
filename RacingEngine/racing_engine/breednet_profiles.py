"""Scrape public Breednet profiles and attach only race-history-verified horses."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .horse_profiles import australian_racing_age, derive_runner_profiles, normalise_country, normalise_sex, record_observation
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "breednet-public-profile"
BASE = "https://www.breednet.com.au/horse/"
PARSER_VERSION = "breednet-profile-v1.0"
TAG = re.compile(r"<[^>]+>")
HEADER = re.compile(r'<div id="HorseHeader"><h1>(.*?)<span[^>]*>\s*\(([A-Z]{2,3})\)\s*(\d{4})</span>', re.S | re.I)
PROFILE = re.compile(r'<div class="horse-profile-row">\s*(\d+)([a-z])\s+(.+?)\s+x\s+(.+?)</div>', re.S | re.I)
FOALED = re.compile(r'<div class="horse-profile-row">Foaled\s+([^<]+)</div>', re.I)
RACE_LINK = re.compile(r'/race-results/([^/"?]+)/([0-9]{4}-[0-9]{2}-[0-9]{2})', re.I)
SEX = {"c": "C", "g": "G", "h": "H", "r": "R", "f": "F", "m": "M"}


def slugify(name: str) -> str:
    value = html.unescape(name).lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG.sub("", value))).strip()


def parse_profile(page: str, source_url: str) -> dict | None:
    header, profile, foaled = HEADER.search(page), PROFILE.search(page), FOALED.search(page)
    if not (header and profile and foaled):
        return None
    birth = datetime.strptime(clean(foaled.group(1)), "%b %d, %Y").date().isoformat()
    sire = clean(profile.group(3)); dam = clean(profile.group(4))
    sire_country_match = re.search(r"\(([A-Z]{2,3})\)\s*$", sire)
    races = sorted({race_date for _, race_date in RACE_LINK.findall(page)})
    return {"name": clean(header.group(1)), "country_code": normalise_country(header.group(2)),
            "foal_year": int(header.group(3)), "current_age": int(profile.group(1)),
            "sex": normalise_sex(SEX.get(profile.group(2).lower())), "birth_date": birth,
            "sire": sire, "dam": dam,
            "sire_country_code": normalise_country(sire_country_match.group(1)) if sire_country_match else None,
            "race_dates": races, "source_url": source_url,
            "content_sha256": hashlib.sha256(page.encode()).hexdigest()}


def fetch_profile(slug: str, *, timeout: int = 30, retries: int = 3) -> tuple[str, str | None, str | None]:
    url = BASE + slug
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": "BetMate-RacingEngine/0.1 profile research"})
            with urlopen(request, timeout=timeout) as response:
                page = response.read().decode("utf-8", "replace")
            return url, page, None
        except HTTPError as exc:
            if exc.code == 404: return url, None, "not_found"
            error = f"http_{exc.code}"
        except (URLError, TimeoutError) as exc:
            error = type(exc).__name__
        if attempt + 1 < retries: time.sleep(0.5 * (attempt + 1))
    return url, None, error


def scrape_profiles(store: RacingStore, *, limit: int | None = None, workers: int = 6,
                    archive_dir: Path | None = None) -> dict:
    horses = store.connection.execute(
        """SELECT h.horse_id,h.canonical_name,group_concat(DISTINCT rr.race_date) race_dates
             FROM horses h JOIN runner_horse_links l ON l.horse_id=h.horse_id
             JOIN runner_results rr USING(source,race_date,track_slug,race_number,runner_number)
            WHERE NOT EXISTS (SELECT 1 FROM horse_profile_observations p
                               WHERE p.horse_id=h.horse_id AND p.birth_date IS NOT NULL)
            GROUP BY h.horse_id,h.canonical_name ORDER BY h.canonical_name""").fetchall()
    if limit is not None: horses = horses[:limit]
    target = archive_dir or ROOT / "data" / "raw" / "breednet_profiles"
    target.mkdir(parents=True, exist_ok=True)
    counts = {key: 0 for key in ("requested", "parsed", "matched", "not_found", "parse_failed", "race_history_mismatch", "errors")}
    counts["requested"] = len(horses); examples = []
    by_slug = {slugify(row["canonical_name"]): row for row in horses}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_profile, slug): slug for slug in by_slug}
        for future in as_completed(futures):
            slug = futures[future]; row = by_slug[slug]
            url, page, error = future.result()
            if page is None:
                counts["not_found" if error == "not_found" else "errors"] += 1
                continue
            parsed = parse_profile(page, url)
            if parsed is None:
                counts["parse_failed"] += 1; continue
            counts["parsed"] += 1
            local_dates = set((row["race_dates"] or "").split(",")); overlap = sorted(local_dates & set(parsed["race_dates"]))
            if not overlap:
                counts["race_history_mismatch"] += 1
                if len(examples) < 10: examples.append({"horse": row["canonical_name"], "url": url, "reason": "no_race_date_overlap"})
                continue
            archive_path = target / f"{slug}.html.gz"
            with gzip.open(archive_path, "wt", encoding="utf-8") as handle: handle.write(page)
            record_observation(store, horse_id=row["horse_id"], profile_source=SOURCE,
                source_horse_id=slug, observed_at=date.today().isoformat(), birth_date=parsed["birth_date"],
                observed_racing_age=None, sex=parsed["sex"], country_code=parsed["country_code"],
                source_url=url, confidence=1.0, detail={"parser_version": PARSER_VERSION,
                    "content_sha256": parsed["content_sha256"], "matched_race_dates": overlap,
                    "sire": parsed["sire"], "dam": parsed["dam"],
                    "sire_country_code": parsed["sire_country_code"], "archive_path": str(archive_path.relative_to(ROOT))})
            counts["matched"] += 1
    derived = derive_runner_profiles(store)
    return {**counts, "derived": derived, "mismatch_examples": examples,
            "source": SOURCE, "parser_version": PARSER_VERSION}


def validate_against_racing_com(store: RacingStore) -> dict:
    rows = store.connection.execute(
        """SELECT b.horse_id,b.birth_date,b.sex breednet_sex,r.observed_at,r.observed_racing_age,r.sex racing_com_sex
             FROM horse_profile_observations b JOIN horse_profile_observations r USING(horse_id)
            WHERE b.profile_source=? AND r.profile_source='racing-com-rv-authorised'""", (SOURCE,)).fetchall()
    age_ok = sex_ok = 0; disagreements = []
    for row in rows:
        calculated = australian_racing_age(row["birth_date"], row["observed_at"])
        age_match = calculated == row["observed_racing_age"]
        sex_match = row["breednet_sex"] == row["racing_com_sex"]
        age_ok += age_match; sex_ok += sex_match
        if (not age_match or not sex_match) and len(disagreements) < 20:
            disagreements.append({"horse_id": row["horse_id"], "calculated_age": calculated,
                "reported_age": row["observed_racing_age"], "breednet_sex": row["breednet_sex"],
                "racing_com_sex": row["racing_com_sex"]})
    return {"comparisons": len(rows), "age_matches": age_ok, "sex_matches": sex_ok,
            "disagreements": disagreements}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--limit", type=int); parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try:
        report = scrape_profiles(store, limit=args.limit, workers=args.workers)
        report["cross_source_validation"] = validate_against_racing_com(store)
    finally: store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else: print(rendered, end="")


if __name__ == "__main__": main()
