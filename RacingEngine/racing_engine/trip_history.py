"""Backfill NSW PDF distance-travelled-versus-winner metrics from cached reports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .rnsw import BASE, parse_sectional_pdf
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "rnsw-authorised"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        pdfs = sorted((ROOT / "data" / "raw" / "rnsw").glob("*/*/sectionals.pdf"))
        if args.dry_run:
            print(json.dumps({"cached_reports": len(pdfs)})); return
        reports = values = 0
        for pdf in pdfs:
            race_date, slug = pdf.parents[1].name, pdf.parent.name
            parsed = parse_sectional_pdf(pdf.read_bytes(), race_date, slug, f"{BASE}/Sectionals/archive.pdf")
            for race in parsed:
                store.enrich_runner_trip_metrics(source=SOURCE, race_date=race_date, track_slug=slug,
                    race_number=race["race_number"], runners=race["runners"])
                values += sum(runner.get("distance_travelled_vs_winner_metres") is not None for runner in race["runners"])
            reports += 1
        print(json.dumps({"reports": reports, "runner_trip_values": values}, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
