"""Authorised internal importer for Racing NSW official result CSV files."""
from __future__ import annotations

import argparse, csv, io, json, re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .storage import RacingStore
from .racing_com import DATE_QUERY, graphql_request

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://racing.racingnsw.com.au"
MEETINGS = {
    "2026-08-01": ("Rosehill Gardens", "rosehill", "0108ROSE"),
    "2026-08-08": ("Royal Randwick", "randwick", "0808RAND"),
}
METRO_VENUES = {
    "rosehill gardens": ("Rosehill Gardens", "rosehill", "ROSE"),
    "royal randwick": ("Royal Randwick", "randwick", "RAND"),
    "randwick": ("Royal Randwick", "randwick", "RAND"),
}

def seconds(value: str) -> float | None:
    value = value.strip()
    if not value: return None
    match = re.fullmatch(r"(?:(\d+)-)?(\d{1,2})\.(\d{1,2})", value)
    if not match: return None
    return int(match.group(1) or 0) * 60 + int(match.group(2)) + int(match.group(3).ljust(2, "0")) / 100

def download(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "BetMate-RacingEngine/0.1 (authorised internal ingestion)"}), timeout=45) as response:
        return response.read()

def discover_saturday_metro_meetings(start_date: str, end_date: str) -> list[dict]:
    """Discover Saturday Randwick/Rosehill meetings before an RNSW backfill."""
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end date must not precede start date")
    meetings: dict[str, dict] = {}
    current = start + timedelta(days=(5 - start.weekday()) % 7)
    while current <= end:
        records = graphql_request(DATE_QUERY, {"date": current.isoformat()}).get("data", {}).get("GetMeetingByDate") or []
        for record in records:
            config = METRO_VENUES.get((record.get("venue") or "").lower())
            if record.get("state") != "NSW" or record.get("isTrial") or record.get("isJumpOut") or not config:
                continue
            venue, slug, suffix = config
            meetings[str(record["id"])] = {"date": current.isoformat(), "venue": venue, "slug": slug,
                                             "sectional_code": current.strftime("%d%m") + suffix}
        current += timedelta(days=7)
    return sorted(meetings.values(), key=lambda meeting: (meeting["date"], meeting["slug"]))


def import_meeting(store: RacingStore, race_date: str, *, venue: str | None = None,
                   slug: str | None = None, sectional_code: str | None = None) -> tuple[int, int]:
    default = MEETINGS.get(race_date)
    if venue is None:
        if default is None:
            discovered = discover_saturday_metro_meetings(race_date, race_date)
            if len(discovered) != 1:
                raise RuntimeError(f"Expected one NSW Saturday metro meeting on {race_date}, found {len(discovered)}.")
            venue, slug, sectional_code = (discovered[0]["venue"], discovered[0]["slug"], discovered[0]["sectional_code"])
        else:
            venue, slug, sectional_code = default
    if not slug or not sectional_code:
        raise ValueError("venue, slug and sectional code are required")
    key = f"{race_date[:4]}{__import__('datetime').date.fromisoformat(race_date).strftime('%b%d')},NSW,{venue}"
    result_url = f"{BASE}/FreeFields/CSV.aspx?" + urlencode({"Key": key, "stage": "Results"})
    csv_bytes = download(result_url)
    archive = ROOT / "data" / "raw" / "rnsw" / race_date / slug
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "results.csv").write_bytes(csv_bytes)
    pdf_url = f"{BASE}/Sectionals/{sectional_code}.pdf"
    try:
        (archive / "sectionals.pdf").write_bytes(download(pdf_url))
    except Exception:
        pass
    rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    meeting = next((row for row in rows if row and row[0] == "Meeting"), None)
    if meeting is None:
        # RNSW returns an HTML error page for historic keys it cannot resolve.
        # Never turn that page into an empty, apparently valid race meeting.
        preview = csv_bytes.decode("utf-8", errors="replace")[:240].replace("\n", " ")
        raise RuntimeError(f"RNSW did not return an official CSV for {race_date} {venue}: {preview}")
    rail, weather, condition = meeting[6], meeting[7], meeting[8]
    current = None; imported_races = 0; imported_runners = 0
    for row in rows:
        if not row: continue
        if row[0] == "Race":
            if current:
                store.upsert_result(source="rnsw-authorised", **current); imported_races += 1; imported_runners += len(current["runners"])
            current = {"race_date": race_date, "state": "NSW", "track_slug": slug, "race_number": int(row[1]),
                "distance_metres": int(row[5]) if row[5].isdigit() else None, "race_class": row[6] or row[3],
                "official_time_seconds": seconds(row[16]), "track_condition": row[14] or condition, "rail_position": rail,
                "source_url": result_url, "raw_race": {"csv": row}, "runners": []}
        elif row[0] == "Horse" and current:
            finish = row[10].strip(); status = "scratched" if finish == "SC" else "finished"
            if status == "finished" and finish.isdigit():
                current["runners"].append({"runner_number": int(re.sub(r"\D", "", row[1])), "runner_name": row[2],
                    "finish_position": int(finish), "beaten_lengths": float(row[13] or 0), "finish_time_seconds": None,
                    "result_status": status, "raw_csv": row})
    if current:
        store.upsert_result(source="rnsw-authorised", **current); imported_races += 1; imported_runners += len(current["runners"])
    return imported_races, imported_runners

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="One NSW Saturday metro date (YYYY-MM-DD)")
    parser.add_argument("--from-date", dest="from_date", help="Discover range start (YYYY-MM-DD)")
    parser.add_argument("--to-date", dest="to_date", help="Discover range end (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Print discovered meetings without downloading cards")
    args = parser.parse_args()
    if bool(args.date) == bool(args.from_date or args.to_date):
        parser.error("Provide either --date or both --from-date and --to-date.")
    if (args.from_date and not args.to_date) or (args.to_date and not args.from_date):
        parser.error("--from-date and --to-date must be used together.")
    meetings = ([{"date": args.date, "venue": None, "slug": None, "sectional_code": None}] if args.date
                else discover_saturday_metro_meetings(args.from_date, args.to_date))
    if args.dry_run:
        print(json.dumps(meetings, indent=2, sort_keys=True)); return
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        totals = [0, 0]
        for meeting in meetings:
            races, runners = import_meeting(store, meeting["date"], venue=meeting["venue"], slug=meeting["slug"], sectional_code=meeting["sectional_code"])
            totals = [left + right for left, right in zip(totals, (races, runners))]
            print(f"Imported {meeting['date']}: {races} RNSW result races and {runners} finishers.")
        print(f"Total: {totals[0]} RNSW result races and {totals[1]} finishers.")
    finally: store.close()

if __name__ == "__main__": main()
