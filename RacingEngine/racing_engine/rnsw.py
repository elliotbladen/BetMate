"""Authorised internal importer for Racing NSW historical result reports.

Racing NSW's legacy CSV endpoint is not consistently retained for old meetings.
The official sectional PDF archive is retained and contains the underlying race
time, each runner's finish time and each reported sectional/position, so it is
the authoritative historical path used here.
"""
from __future__ import annotations

import argparse, csv, io, json, re
from io import BytesIO
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pypdf import PdfReader

from .storage import RacingStore
from .racing_com import DATE_QUERY, graphql_request, import_meeting as import_structured_result

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://racing.racingnsw.com.au"
MEETINGS = {
    "2026-08-01": ("Rosehill Gardens", "rosehill", "0108ROSE"),
    "2026-08-08": ("Royal Randwick", "randwick", "0808RAND"),
}
METRO_VENUES = {
    # Rosehill changed archive identifier from RHIL to ROSE.  Try both rather
    # than guessing a switchover date and silently missing historic meetings.
    "rosehill gardens": ("Rosehill Gardens", "rosehill", "ROSE"),
    "royal randwick": ("Royal Randwick", "randwick", "RAND"),
    "randwick": ("Royal Randwick", "randwick", "RAND"),
}

RACE_HEADER = re.compile(r"Race\s+(\d+)\s*:\s*(.+?)\s*-\s*(\d+)m\b", re.I)
TRACK_LINE = re.compile(r"Track Rating:\s*([^,\n]+).*?Rail Position:\s*([^\n]+)", re.I)
TIME_TOKEN = re.compile(r"(\d+:\d{2}\.\d{2})\s*\[([0-9-]+)\]")
# The final columns vary between the legacy and newer report layouts.  The
# stable fields are rank, TAB number, horse name and its overall clock.
RUNNER_LINE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(.+?)\s{2,}(\d+:\d{2}\.\d{2})\b.*$", re.M)


def distance_travelled_by_runner(text: str) -> dict[int, float]:
    """Extract RNSW's DT-W value on the jockey/margin line after a runner."""
    values: dict[int, float] = {}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = RUNNER_LINE.fullmatch(line)
        if not match:
            continue
        # The following line contains `(barrier) jockey ... margin (DT-W)`.
        # Only accept a signed/final parenthesised number, never the barrier.
        following = lines[index + 1] if index + 1 < len(lines) else ""
        travelled = re.search(r"\d+(?:\.\d+)?L\s+\(([-+]\d+)\)", following)
        if travelled:
            values[int(match.group(2))] = float(travelled.group(1))
    return values


def clock_seconds(value: str) -> float:
    minutes, seconds_part = value.split(":", 1)
    return int(minutes) * 60 + float(seconds_part)


def sectional_codes(sectional_code: str) -> list[str]:
    """Return archive code candidates, including historical Rosehill RHIL."""
    if sectional_code.endswith("ROSE"):
        prefix = sectional_code[:-4]
        return [sectional_code, prefix + "RHIL"]
    return [sectional_code]


def download_sectional_pdf(sectional_code: str) -> tuple[bytes, str]:
    errors: list[str] = []
    for code in sectional_codes(sectional_code):
        url = f"{BASE}/Sectionals/{code}.pdf"
        try:
            content = download(url)
            if content.startswith(b"%PDF"):
                return content, url
            errors.append(f"{code}: not a PDF")
        except Exception as exc:  # try the legacy Rosehill code before failing
            errors.append(f"{code}: {exc}")
    raise RuntimeError("No official RNSW sectional PDF found (" + "; ".join(errors) + ")")


def _race_markers(text: str, distance_metres: int | None = None) -> tuple[list[int], bool]:
    line = next((line for line in text.splitlines() if "Distance To Go" in line), "")
    markers = [int(value) for value in re.findall(r"(\d+)m", line)]
    if markers:
        # Long races are printed across horizontal report pages.  Only the
        # final page has a Finish column; do not invent a zero marker earlier.
        return markers + ([0] if re.search(r"\bFinish\b", line, re.I) else []), False
    # TripleSData's newer report format uses L1100/L1000 headers and reports
    # time remaining, rather than the legacy "Distance To Go" headings.
    header = next((value for value in text.splitlines() if "Rank" in value and re.search(r"\bL\d+", value)), "")
    values = [int(value) for value in re.findall(r"\bL(\d+)\b", header)]
    if values and distance_metres and values[0] == distance_metres:
        values = values[1:]
    return (values + [0] if values else []), bool(values)


def parse_sectional_pdf(pdf_bytes: bytes, race_date: str, slug: str, source_url: str) -> list[dict]:
    """Parse Racing NSW's fixed-width two-page-per-race sectional report.

    The PDF supplies cumulative times at distance-to-go markers.  Storage uses
    per-section duration, which we derive deterministically from those values.
    Margin is intentionally left null: it is not reliably represented in the
    text layer, while runner finish times are present for every finisher.
    """
    races_by_number: dict[int, dict] = {}
    current: dict | None = None
    for page in PdfReader(BytesIO(pdf_bytes)).pages:
        text = page.extract_text(extraction_mode="layout") or ""
        header = RACE_HEADER.search(text)
        if header:
            race_number = int(header.group(1))
            current = races_by_number.get(race_number)
            condition, rail = None, None
            track = TRACK_LINE.search(text)
            if track:
                condition, rail = track.group(1).strip(), track.group(2).strip()
            field_line = next((line for line in text.splitlines() if line.strip().startswith("Field Times")), "")
            field_times = re.findall(r"\d+:\d{2}\.\d{2}", field_line)
            if current is None:
                current = {
                    "race_date": race_date, "state": "NSW", "track_slug": slug,
                    "race_number": race_number, "distance_metres": int(header.group(3)),
                    "race_class": header.group(2).strip(), "official_time_seconds": None,
                    "track_condition": condition, "rail_position": rail, "source_url": source_url,
                    "raw_race": {"pages": []}, "runners": [],
                }
                races_by_number[race_number] = current
            # Wide reports spill horizontally: a race can have several pages,
            # each with a separate marker range.  Only the last page carries
            # the official time, so retain it when present.
            if "Official" in field_line and field_times:
                current["official_time_seconds"] = clock_seconds(field_times[-1])
            markers, reverse_time_layout = _race_markers(text, current["distance_metres"])
            current["raw_race"]["pages"].append({"text": text, "markers": markers,
                                                     "reverse_time_layout": reverse_time_layout})
        elif current is not None:
            markers, reverse_time_layout = _race_markers(text, current["distance_metres"])
            current["raw_race"]["pages"].append({"text": text, "markers": markers,
                                                     "reverse_time_layout": reverse_time_layout})

    for race in races_by_number.values():
        runner_parts: dict[tuple[int, int], dict] = {}
        for page in race["raw_race"]["pages"]:
            page_markers = page["markers"]
            page_trip = distance_travelled_by_runner(page["text"])
            for match in RUNNER_LINE.finditer(page["text"]):
                finish_position, runner_number = int(match.group(1)), int(match.group(2))
                key = (finish_position, runner_number)
                tokens = TIME_TOKEN.findall(match.group(0))
                if not page_markers:
                    continue
                runner = runner_parts.setdefault(key, {"runner_number": runner_number,
                    "runner_name": re.sub(r"\s+", " ", match.group(3)).strip(),
                    "finish_position": finish_position, "points": [], "distance_travelled_vs_winner_metres": None})
                if runner_number in page_trip:
                    runner["distance_travelled_vs_winner_metres"] = page_trip[runner_number]
                if page["reverse_time_layout"]:
                    # New report: bracketed values are time remaining.  The
                    # first unbracketed clock after the horse is overall time.
                    clocks = re.findall(r"\d+:\d{2}\.\d{2}", match.group(0))
                    if not clocks or len(tokens) < len(page_markers) - 1:
                        continue
                    overall = clock_seconds(clocks[0])
                    for marker, (value, position) in zip(page_markers[:-1], tokens):
                        runner["points"].append((marker, overall - clock_seconds(value),
                                                 int(position) if position != "-" else None))
                    runner["points"].append((0, overall, finish_position))
                elif len(tokens) >= len(page_markers):
                    for marker, (value, position) in zip(page_markers, tokens[-len(page_markers):]):
                        runner["points"].append((marker, clock_seconds(value), int(position) if position != "-" else None))
        for runner in runner_parts.values():
            # Reports occasionally duplicate pages.  A marker is unique within
            # a runner, so preserve first observed value in report order.
            points_by_marker = {marker: (elapsed, position) for marker, elapsed, position in runner["points"]}
            ordered = sorted(points_by_marker.items(), key=lambda item: item[0], reverse=True)
            previous, sections = 0.0, []
            for marker, (elapsed, position) in ordered:
                sections.append({"marker_metres": marker, "section_seconds": round(elapsed - previous, 3),
                    "position_at_marker": position, "distance_travelled_metres": None, "speed_kmh": None,
                    "source_url": source_url, "raw_sectional": {"cumulative_seconds": elapsed}})
                previous = elapsed
            if not sections:
                continue
            race["runners"].append({"runner_number": runner["runner_number"], "runner_name": runner["runner_name"],
                "finish_position": runner["finish_position"], "beaten_lengths": None,
                "distance_travelled_vs_winner_metres": runner["distance_travelled_vs_winner_metres"],
                "finish_time_seconds": next((elapsed for marker, (elapsed, _) in ordered if marker == 0), None),
                "result_status": "finished", "raw_csv": {"pdf_points": runner["points"]}, "sectionals": sections})
        # TripleSData's newer layout supplies every runner's overall clock but
        # may omit the legacy ``Field Times ... Official`` line.  The winner's
        # reported overall clock is the official race time; retain it rather
        # than leaving an otherwise complete race unusable by the par model.
        if race["official_time_seconds"] is None:
            winner = next((runner for runner in race["runners"]
                           if runner["finish_position"] == 1
                           and runner["finish_time_seconds"] is not None), None)
            if winner is not None:
                race["official_time_seconds"] = winner["finish_time_seconds"]
    return list(races_by_number.values())

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
                                             "meet_code": str(record["id"]),
                                             "sectional_code": current.strftime("%d%m") + suffix}
        current += timedelta(days=7)
    return sorted(meetings.values(), key=lambda meeting: (meeting["date"], meeting["slug"]))


def import_meeting(store: RacingStore, race_date: str, *, venue: str | None = None,
                   slug: str | None = None, sectional_code: str | None = None,
                   meet_code: str | None = None, results_only: bool = False) -> tuple[int, int]:
    default = MEETINGS.get(race_date)
    if venue is None:
        if default is None:
            discovered = discover_saturday_metro_meetings(race_date, race_date)
            if len(discovered) != 1:
                raise RuntimeError(f"Expected one NSW Saturday metro meeting on {race_date}, found {len(discovered)}.")
            venue, slug, sectional_code, meet_code = (discovered[0]["venue"], discovered[0]["slug"],
                discovered[0]["sectional_code"], discovered[0]["meet_code"])
        else:
            venue, slug, sectional_code = default
    if not slug or not sectional_code:
        raise ValueError("venue, slug and sectional code are required")
    # Result identity is acquired independently of sectional availability.
    # A missing archive PDF must never make an otherwise valid result vanish.
    if meet_code is None:
        discovered = discover_saturday_metro_meetings(race_date, race_date)
        match = next((item for item in discovered if item["slug"] == slug), None)
        if match is None:
            raise RuntimeError("No structured official result card found for NSW meeting")
        meet_code = match["meet_code"]
    result_source = "racing-com-nsw-authorised-v2"
    imported_races, imported_runners, _ = import_structured_result(
        store, race_date, meet_code=meet_code, slug=slug,
        expected_state="NSW", source=result_source)
    if results_only:
        return imported_races, imported_runners
    # The official report archive is the primary historical source.  The CSV
    # endpoint below is retained only as a fallback for a future report change.
    archive = ROOT / "data" / "raw" / "rnsw" / race_date / slug
    archive.mkdir(parents=True, exist_ok=True)
    try:
        cached_pdf = archive / "sectionals.pdf"
        if cached_pdf.exists() and cached_pdf.read_bytes()[:4] == b"%PDF":
            pdf_bytes = cached_pdf.read_bytes()
            pdf_url = f"{BASE}/Sectionals/{sectional_code}.pdf"
        else:
            pdf_bytes, pdf_url = download_sectional_pdf(sectional_code)
            cached_pdf.write_bytes(pdf_bytes)
        races = parse_sectional_pdf(pdf_bytes, race_date, slug, pdf_url)
        if not races or not any(race["runners"] for race in races):
            raise RuntimeError("PDF did not contain any parseable finishing runners")
        # V2 ownership rule: the structured result card is the only source of
        # runner identity and finishing result.  The sectional PDF may enrich
        # an official runner number, but must never manufacture a horse/result.
        sectional_rows: list[dict] = []
        for race in races:
            official_numbers = {int(row[0]) for row in store.connection.execute(
                """SELECT runner_number FROM runner_results WHERE source=? AND race_date=?
                   AND track_slug=? AND race_number=?""",
                (result_source, race_date, slug, race["race_number"]))}
            for runner in race["runners"]:
                if runner["runner_number"] not in official_numbers:
                    continue
                for sectional in runner.get("sectionals", []):
                    sectional_rows.append({"source": result_source, "race_date": race_date,
                        "track_slug": slug, "race_number": race["race_number"],
                        "runner_number": runner["runner_number"], **sectional})
        store.upsert_sectionals(sectional_rows)
        return imported_races, imported_runners
    except Exception as pdf_error:
        # Sectionals are optional evidence in V2.  Preserve the structured
        # official results and leave the unavailable PDF explicitly absent.
        return imported_races, imported_runners
    # V2 never falls back to the legacy CSV/PDF text as a result identity
    # source.  The code below is retained temporarily for forensic comparison
    # with V1, but is unreachable by design.
    pdf_failure = str(pdf_error)
    key = f"{race_date[:4]}{__import__('datetime').date.fromisoformat(race_date).strftime('%b%d')},NSW,{venue}"
    result_url = f"{BASE}/FreeFields/CSV.aspx?" + urlencode({"Key": key, "stage": "Results"})
    csv_bytes = download(result_url)
    (archive / "results.csv").write_bytes(csv_bytes)
    rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    meeting = next((row for row in rows if row and row[0] == "Meeting"), None)
    if meeting is None:
        # RNSW returns an HTML error page for historic keys it cannot resolve.
        # Never turn that page into an empty, apparently valid race meeting.
        preview = csv_bytes.decode("utf-8", errors="replace")[:240].replace("\n", " ")
        raise RuntimeError(
            f"RNSW did not return a parseable official report for {race_date} {venue}. "
            f"PDF error: {pdf_failure}. CSV response: {preview}"
        )
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
    parser.add_argument("--results-only", action="store_true", help="Import structured result cards without parsing sectional PDFs")
    args = parser.parse_args()
    if bool(args.date) == bool(args.from_date or args.to_date):
        parser.error("Provide either --date or both --from-date and --to-date.")
    if (args.from_date and not args.to_date) or (args.to_date and not args.from_date):
        parser.error("--from-date and --to-date must be used together.")
    meetings = ([{"date": args.date, "venue": None, "slug": None, "sectional_code": None, "meet_code": None}] if args.date
                else discover_saturday_metro_meetings(args.from_date, args.to_date))
    if args.dry_run:
        print(json.dumps(meetings, indent=2, sort_keys=True)); return
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        totals = [0, 0]; failures: list[str] = []
        for meeting in meetings:
            try:
                races, runners = import_meeting(store, meeting["date"], venue=meeting["venue"], slug=meeting["slug"], sectional_code=meeting["sectional_code"], meet_code=meeting.get("meet_code"), results_only=args.results_only)
                totals = [left + right for left, right in zip(totals, (races, runners))]
                print(f"Imported {meeting['date']}: {races} RNSW result races and {runners} finishers.")
            except Exception as exc:
                failures.append(f"{meeting['date']} {meeting['venue']}: {exc}")
                print(f"Skipped {meeting['date']} {meeting['venue']}: {exc}")
        print(f"Total: {totals[0]} RNSW result races and {totals[1]} finishers.")
        if failures:
            print(f"Unavailable meetings ({len(failures)}):\n" + "\n".join(failures))
    finally: store.close()

if __name__ == "__main__": main()
