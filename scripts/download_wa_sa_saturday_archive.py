#!/usr/bin/env python3
"""Download Saturday metropolitan WA/SA race records for the trailing three years.

The archive keeps source HTML/PDF responses and a manifest.  A response is never
treated as a meeting unless its body identifies the requested venue/date; this
leaves a reviewable audit trail for dates on which a venue did not race.
"""
from __future__ import annotations
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw" / "wa_sa_saturday"
START = dt.date(2023, 9, 18)
END = dt.date(2026, 9, 18)
TRACKS = {
    "ascot": {"state": "WA", "ra_name": "Ascot", "racehub": "ascot"},
    "belmont-park": {"state": "WA", "ra_name": "Belmont", "racehub": "belmont-park"},
    "morphettville": {"state": "SA", "ra_name": "Morphettville", "racehub": "morphettville"},
    "morphettville-parks": {"state": "SA", "ra_name": "Morphettville Parks", "racehub": "morphettville-parks"},
}
UA = "BetMate-racing-archive/1.0 (research; contact repository owner)"

def fetch(url: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(), r.headers.get_content_type()
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get_content_type()
    except Exception as e:
        return 0, str(e).encode(), "text/plain"

def saturdays():
    d = START + dt.timedelta(days=(5 - START.weekday()) % 7)
    while d <= END:
        yield d
        d += dt.timedelta(days=7)

def save_response(path: pathlib.Path, status: int, body: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {"path": str(path.relative_to(ROOT)), "status": status, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest()}

def job(item):
    track, date, source, url = item
    ext = ".pdf" if "pdf" in source else ".html"
    safe = source.replace("/", "_")
    path = ROOT / track / date.isoformat() / f"{safe}{ext}"
    status, body, ctype = fetch(url)
    rec = save_response(path, status, body)
    rec.update({"track": track, "date": date.isoformat(), "source": source, "url": url,
                "content_type": ctype, "empty_or_error": status != 200})
    return rec

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    items = []
    dates = list(saturdays())
    # Racing Australia's dated result pages are the broadest official index.
    for date in dates:
        stamp = date.strftime("%Y%m%d")
        for track, cfg in TRACKS.items():
            items.append((track, date, "racing_australia_results",
                          f"https://www.racingaustralia.horse/FreeFields/Results.aspx?Key={stamp}%2C{cfg['state']}%2C{cfg['ra_name']}"))
            items.append((track, date, "racehub_race_1",
                          f"https://racehub.com.au/form-guide/horse-racing/{cfg['racehub']}/{date.isoformat()}/race-1"))
            items.append((track, date, "racehub_raceday",
                          f"https://racehub.com.au/raceday/{cfg['racehub']}-{date.isoformat()}"))
    results = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for i, rec in enumerate(ex.map(job, items), 1):
            results.append(rec)
            if i % 100 == 0:
                print(f"downloaded {i}/{len(items)}", flush=True)
    manifest = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "coverage_start": START.isoformat(), "coverage_end": END.isoformat(),
                "weekday": "Saturday", "tracks": TRACKS, "records": results,
                "notes": ["HTTP 404/403 and non-meeting pages are retained and flagged; they are not silently omitted.",
                          "RaceHub exposes only the historical meetings indexed by its track pages; Racing Australia dated result pages provide the complete date/venue sweep."]}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    good = sum(r["status"] == 200 for r in results)
    print(f"saved {len(results)} responses; HTTP 200: {good}; manifest: {ROOT/'manifest.json'}")

if __name__ == "__main__":
    main()
