"""Import a real NSW or Victorian Saturday metropolitan card from FormFav."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from .formfav import FormFavClient, FormFavError
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

# The first-year scope is metropolitan Saturday meetings. Extend this mapping
# deliberately as regional NSW/Victoria cards are brought into scope.
METRO_TRACKS = {
    "NSW": {"randwick", "rosehill"},
    "VIC": {"caulfield", "flemington", "moonee-valley"},
}


def archive_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def select_meetings(payload: dict[str, Any], state: str) -> list[dict[str, Any]]:
    allowed = METRO_TRACKS[state]
    return [meeting for meeting in payload.get("meetings", []) if meeting.get("slug") in allowed]


def import_state(client: FormFavClient, store: RacingStore, race_date: str, state: str) -> tuple[int, int]:
    run_id = store.start_run(race_date, state)
    try:
        meetings_payload = client.meetings(race_date)
        archive_json(DATA_DIR / "raw" / "formfav" / race_date / "meetings.json", meetings_payload)
        meetings = select_meetings(meetings_payload, state)
        if not meetings:
            store.finish_run(run_id, "empty", "No metropolitan meeting matched the configured first-year scope.")
            return 0, 0

        imported_races = 0
        imported_runners = 0
        for meeting in meetings:
            cards: list[dict[str, Any]] = []
            for race in meeting.get("races", []):
                race_number = race.get("raceNumber")
                if race_number is None or race.get("abandoned"):
                    continue
                card = client.race_form(race_date, str(meeting["slug"]), int(race_number))
                cards.append(card)
                archive_json(
                    DATA_DIR / "raw" / "formfav" / race_date / state.lower() / str(meeting["slug"]) / f"race_{int(race_number):02d}.json",
                    card,
                )
            imported_races += len(cards)
            imported_runners += store.upsert_card(race_date, state, meeting, cards)
        store.finish_run(run_id, "success", f"Imported {imported_races} races and {imported_runners} runners.")
        return imported_races, imported_runners
    except Exception as error:
        store.finish_run(run_id, "failed", str(error))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat(), help="Saturday date in YYYY-MM-DD format")
    parser.add_argument("--state", choices=("NSW", "VIC", "all"), default="all")
    args = parser.parse_args()

    client = FormFavClient()
    store = RacingStore(DATA_DIR / "racing_engine.sqlite")
    try:
        states = ("NSW", "VIC") if args.state == "all" else (args.state,)
        for state in states:
            races, runners = import_state(client, store, args.date, state)
            print(f"{state}: imported {races} races and {runners} runners")
    except FormFavError as error:
        raise SystemExit(str(error)) from error
    finally:
        store.close()


if __name__ == "__main__":
    main()
