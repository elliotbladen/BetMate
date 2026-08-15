"""Authorised internal importer for Racing NSW official result CSV files."""
from __future__ import annotations

import argparse, csv, io, json, re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://racing.racingnsw.com.au"
MEETINGS = {
    "2026-08-01": ("Rosehill Gardens", "rosehill", "0108ROSE"),
    "2026-08-08": ("Royal Randwick", "randwick", "0808RAND"),
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

def import_meeting(store: RacingStore, race_date: str) -> tuple[int, int]:
    venue, slug, sectional_code = MEETINGS[race_date]
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
    meeting = next(row for row in rows if row and row[0] == "Meeting")
    rail, weather, condition = meeting[6], meeting[7], meeting[8]
    current = None; imported_races = 0; imported_runners = 0
    for row in rows:
        if not row: continue
        if row[0] == "Race":
            if current:
                store.upsert_result(source="rnsw-authorised", **current); imported_races += 1; imported_runners += len(current["runners"])
            current = {"race_date": race_date, "state": "NSW", "track_slug": slug, "race_number": int(row[1]),
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
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--date", choices=tuple(MEETINGS), required=True); args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        races, runners = import_meeting(store, args.date); print(f"Imported {races} RNSW result races and {runners} finishers.")
    finally: store.close()

if __name__ == "__main__": main()
