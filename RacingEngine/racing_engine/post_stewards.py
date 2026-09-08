"""Authorised importer for Racing Australia post-race stewards reports (NSW).

Racing Australia publishes a per-meeting "Post Stewards" PDF at
``https://racingaustralia.horse/PostStewardsReports/{DDMMYYYY}{CODE}.pdf``. For
NSW Saturday metropolitan meetings this is the official stewards' report: the
racing.com form feed consumed by :mod:`racing_engine.steward_reports` only ever
carries the Victorian reports.

Parsing is deliberately conservative and reuses the shared rule classifier in
:mod:`racing_engine.stewards`, so a NSW comment and a VIC comment of the same
wording receive the same category, severity and provisional trip figure. Those
figures remain research/review evidence only; V1/V3 ratings do not consume them.

The unmodified PDF is archived under ``data/raw/post_stewards/`` so every stored
event stays auditable back to its source.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from html import escape
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader

from .stewards import PARSER_VERSION as RULE_VERSION, classify_report, plain_text
from .storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "post_stewards"

REPORT_SOURCE = "racing-australia-post-stewards"
PARSER_VERSION = f"{RULE_VERSION}+post-stewards-pdf-v1"
BASE = "https://racingaustralia.horse/PostStewardsReports"
USER_AGENT = "BetMate-RacingEngine/0.1 (authorised internal ingestion)"

# Meeting codes used in the Post Stewards filename. The first candidate that
# returns a PDF wins; Rosehill has appeared under more than one historical code.
VENUE_CODES = {
    "randwick": ("RAND",),
    "rosehill": ("RHIL", "ROSE"),
    "warwick-farm": ("WFM", "WFRM"),
    "canterbury": ("CANT",),
    "kembla-grange": ("KEM", "KEMB"),
    "hawkesbury": ("HAW", "HAWK"),
    "newcastle": ("NCLE", "NEWC"),
    "gosford": ("GOS", "GOSF"),
}

_HEADER_RE = re.compile(r"RACE\s+(\d+):\s*(.+?)\s+(\d+)m\s*:?(?=\s)")
_GENERAL_RE = re.compile(r"\n\s*GENERAL\s*:", re.IGNORECASE)
# A steward paragraph starts "<Horse Name> - ...". Horse names are 1-6 title-case
# tokens, optionally with a country suffix, followed by a hyphen or dash.
_NAME = r"(?:[A-Z][A-Za-z'.]+)(?:\s+(?:[A-Z][A-Za-z'.]+|On|The|A|Of|To|In|And))*"
_SPLIT_RE = re.compile(r"(?<=[.)])\s+(?=" + _NAME + r"\s*(?:\([A-Z]{2,4}\)\s*)?[\-–—]\s)")


def _download(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as response:
        return response.read()


def fetch_report_pdf(race_date: str, track_slug: str) -> tuple[bytes, str]:
    """Return ``(pdf_bytes, source_url)`` for a meeting's post-stewards report."""
    codes = VENUE_CODES.get(track_slug)
    if not codes:
        raise ValueError(f"No Racing Australia post-stewards code configured for {track_slug}")
    stamp = date.fromisoformat(race_date).strftime("%d%m%Y")
    errors: list[str] = []
    for code in codes:
        url = f"{BASE}/{stamp}{code}.pdf"
        try:
            content = _download(url)
        except Exception as exc:  # 404 until the report publishes; try the next code
            errors.append(f"{code}: {exc}")
            continue
        if content[:4] == b"%PDF":
            return content, url
        errors.append(f"{code}: not a PDF")
    raise RuntimeError(f"No post-stewards PDF for {race_date} {track_slug} (" + "; ".join(errors) + ")")


def pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def clean_report_text(text: str) -> str:
    """Normalise the source's typographic punctuation and drop page stamps.

    The report uses en dashes ("Decorum – Held up") and curly apostrophes
    ("King’s Secret"); fold both to ASCII so the paragraph split and the
    stored evidence text are stable. U+FFFD is also folded defensively for text
    layers that mangle the source apostrophe.
    """
    text = text.replace("’", "'").replace("‘", "'").replace("�", "'")
    text = text.replace("–", "-").replace("—", "-")
    # Running page stamp, e.g. "20260905RR 3".
    text = re.sub(r"(?m)^\s*\d{8}[A-Z]{2}\s+\d+\s*$", "", text)
    return text


def parse_races(report_text: str) -> list[dict]:
    """Split a cleaned report into ``{race_number, race_name, distance_metres, paragraphs}``.

    Only the per-race ``RACE n:`` blocks are returned; the meeting header and the
    ``GENERAL``/``SUMMARY`` trailer are intentionally not stored, matching the
    per-race scope of the Victorian importer.
    """
    text = clean_report_text(report_text)
    headers = list(_HEADER_RE.finditer(text))
    if not headers:
        return []
    trailer = _GENERAL_RE.search(text)
    tail = trailer.start() if trailer else len(text)
    races: list[dict] = []
    for index, header in enumerate(headers):
        start = header.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else tail
        block = re.sub(r"\s+", " ", text[start:end]).strip()
        paragraphs = [part.strip() for part in _SPLIT_RE.split(block) if part.strip()] if block else []
        races.append({
            "race_number": int(header.group(1)),
            "race_name": header.group(2).strip(),
            "distance_metres": int(header.group(3)),
            "paragraphs": paragraphs,
        })
    return races


def paragraphs_to_html(paragraphs: list[str]) -> str:
    return "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)


def _runner_names(connection, race_date: str, track_slug: str, race_number: int) -> list[str]:
    rows = connection.execute(
        """SELECT DISTINCT runner_name FROM runner_results
           WHERE race_date = ? AND track_slug = ? AND race_number = ?""",
        (race_date, track_slug, race_number),
    ).fetchall()
    return [row[0] for row in rows if row[0]]


def import_meeting(store: RacingStore, race_date: str, track_slug: str) -> dict:
    pdf_bytes, source_url = fetch_report_pdf(race_date, track_slug)
    archive = RAW_DIR / race_date
    archive.mkdir(parents=True, exist_ok=True)
    (archive / f"{track_slug}.pdf").write_bytes(pdf_bytes)

    races = parse_races(pdf_text(pdf_bytes))
    reports = events = 0
    for race in races:
        names = _runner_names(store.connection, race_date, track_slug, race["race_number"])
        html = paragraphs_to_html(race["paragraphs"])
        extracted = classify_report(html, names) if names else []
        store.upsert_steward_report(
            report_source=REPORT_SOURCE, race_date=race_date, track_slug=track_slug,
            race_number=race["race_number"], source_race_code=None,
            report_html=html, report_text=plain_text(html),
            source_updated_at=None, source_url=source_url,
            parser_version=PARSER_VERSION, events=extracted,
        )
        reports += 1
        events += len(extracted)
    return {"track_slug": track_slug, "source_url": source_url, "reports": reports, "events": events}


def _targets(store: RacingStore, race_date: str | None, track: str | None):
    clauses = ["state = 'NSW'"]
    params: list[str] = []
    if race_date:
        clauses.append("race_date = ?")
        params.append(race_date)
    if track:
        clauses.append("track_slug = ?")
        params.append(track)
    where = " AND ".join(clauses)
    return store.connection.execute(
        f"""SELECT DISTINCT race_date, track_slug FROM race_results
            WHERE {where}
              AND NOT EXISTS (
                SELECT 1 FROM steward_report_ingestions si
                 WHERE si.report_source = ? AND si.race_date = race_results.race_date
                   AND si.track_slug = race_results.track_slug AND si.status = 'complete')
            ORDER BY race_date, track_slug""",
        (*params, REPORT_SOURCE),
    ).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Import only meetings on this ISO date (YYYY-MM-DD).")
    parser.add_argument("--track", help="Restrict to a single track slug, e.g. randwick.")
    parser.add_argument("--dry-run", action="store_true", help="List pending meetings and exit.")
    args = parser.parse_args()

    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        targets = _targets(store, args.date, args.track)
        if args.dry_run:
            print(json.dumps([dict(row) for row in targets], indent=2))
            return
        totals = {"meetings": 0, "reports": 0, "events": 0, "errors": 0}
        for row in targets:
            race_date, track_slug = row["race_date"], row["track_slug"]
            try:
                result = import_meeting(store, race_date, track_slug)
                store.record_steward_report_check(
                    report_source=REPORT_SOURCE, race_date=race_date, track_slug=track_slug,
                    status="complete", detail=f"post-stewards PDF imported ({result['reports']} races)",
                )
                totals["meetings"] += 1
                totals["reports"] += result["reports"]
                totals["events"] += result["events"]
                print(f"{race_date} {track_slug}: {result['reports']} races, {result['events']} events "
                      f"({result['source_url']})", flush=True)
            except Exception as exc:
                totals["errors"] += 1
                store.record_steward_report_check(
                    report_source=REPORT_SOURCE, race_date=race_date, track_slug=track_slug,
                    status="error", detail=str(exc)[:500],
                )
                print(f"Skipped {race_date} {track_slug}: {exc}", flush=True)
        print(json.dumps(totals, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
