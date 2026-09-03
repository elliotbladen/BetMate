"""Backfill year-qualified ATC Swiss Timing reports into existing NSW results."""
from __future__ import annotations

import argparse

from .horse_identity import identity_key
from .rnsw import ROOT, download_atc_sectional_pdf, parse_sectional_pdf
from .storage import RacingStore

SOURCE = "racing-com-nsw-authorised-v2"


def import_meeting(store: RacingStore, race_date: str, slug: str) -> tuple[int, int]:
    archive = ROOT / "data" / "raw" / "rnsw" / race_date / slug
    archive.mkdir(parents=True, exist_ok=True)
    cached = archive / "atc-sectionals.pdf"
    if cached.exists() and cached.read_bytes()[:4] == b"%PDF":
        payload = cached.read_bytes()
        code = "RHIL" if slug == "rosehill" else "RAND"
        url = f"https://feed.australianturfclub.com.au/sectionals/swiss-timing/{race_date[:4]}/{race_date[8:10]}{race_date[5:7]}{code}.pdf"
    else:
        payload, url = download_atc_sectional_pdf(race_date, slug)
        cached.write_bytes(payload)
    races = parse_sectional_pdf(payload, race_date, slug, url)
    # A few Racing.com result payloads have their race numbers displaced from
    # the published ATC card (most notably the 2025 autumn carnival).  Resolve
    # the target race by the field itself, rather than trusting equal numbers.
    official_by_race: dict[int, dict[int, str]] = {}
    for row in store.connection.execute(
        "SELECT race_number,runner_number,runner_name FROM runner_results "
        "WHERE source=? AND race_date=? AND track_slug=?",
        (SOURCE, race_date, slug),
    ):
        official_by_race.setdefault(int(row[0]), {})[int(row[1])] = identity_key(row[2])

    sectional_rows = []
    matched = 0
    for race in races:
        report_field = {int(r["runner_number"]): identity_key(r["runner_name"])
                        for r in race["runners"]}
        def field_score(item: tuple[int, dict[int, str]]) -> tuple[int, int, int]:
            candidate_number, field = item
            exact = sum(field.get(number) == name for number, name in report_field.items())
            identity_overlap = len(set(field.values()) & set(report_field.values()))
            same_number = int(candidate_number == race["race_number"])
            return exact, identity_overlap, same_number
        target_race_number, official = max(official_by_race.items(), key=field_score)
        exact, identity_overlap, _ = field_score((target_race_number, official))
        if not report_field or (exact == 0 and identity_overlap < 2):
            continue
        if race.get("official_time_seconds") is not None:
            store.connection.execute("UPDATE race_results SET official_time_seconds=?,source_url=? WHERE source=? AND race_date=? AND track_slug=? AND race_number=?",
                (race["official_time_seconds"], url, SOURCE, race_date, slug, target_race_number))
        for runner in race["runners"]:
            number = runner["runner_number"]
            if official.get(number) != identity_key(runner["runner_name"]):
                continue
            matched += 1
            store.connection.execute("UPDATE runner_results SET finish_time_seconds=?,distance_travelled_vs_winner_metres=? WHERE source=? AND race_date=? AND track_slug=? AND race_number=? AND runner_number=?",
                (runner.get("finish_time_seconds"), runner.get("distance_travelled_vs_winner_metres"), SOURCE, race_date, slug, target_race_number, number))
            for sectional in runner.get("sectionals", []):
                sectional_rows.append({"source": SOURCE, "race_date": race_date, "track_slug": slug,
                    "race_number": target_race_number, "runner_number": number, **sectional})
    store.upsert_sectionals(sectional_rows)
    store.connection.commit()
    return len(races), matched


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--from-date", required=True); p.add_argument("--to-date", required=True)
    a = p.parse_args(); store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    meetings = store.connection.execute("SELECT DISTINCT race_date,track_slug FROM race_results WHERE source=? AND race_date>=? AND race_date<=? AND track_slug IN ('randwick','rosehill') ORDER BY race_date,track_slug",
        (SOURCE, a.from_date, a.to_date)).fetchall()
    totals = [0, 0]; failures = []
    try:
        for meeting in meetings:
            try:
                counts = import_meeting(store, meeting["race_date"], meeting["track_slug"])
                totals[0] += counts[0]; totals[1] += counts[1]
                print(f'{meeting["race_date"]} {meeting["track_slug"]}: {counts[0]} races, {counts[1]} runners', flush=True)
            except Exception as exc:
                failures.append(f'{meeting["race_date"]}|{meeting["track_slug"]}: {exc}')
                print(f'FAILED {failures[-1]}', flush=True)
    finally: store.close()
    print(f'Total: {totals[0]} races, {totals[1]} matched runners; failures={len(failures)}')


if __name__ == "__main__": main()
