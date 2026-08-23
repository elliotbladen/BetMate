"""Readiness gate for weekday, provincial, country and interstate expansion."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .storage import RacingStore


TARGET_STATES = ("NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT")


def report(store: RacingStore) -> dict[str, Any]:
    state_counts = {row["state"]: row["races"] for row in store.connection.execute(
        "SELECT state,count(*) races FROM race_results GROUP BY state")}
    weekdays = Counter()
    for row in store.connection.execute("SELECT race_date,count(*) races FROM race_results GROUP BY race_date"):
        from datetime import date
        weekdays[date.fromisoformat(row["race_date"]).strftime("%A")] += row["races"]
    missing_states = [state for state in TARGET_STATES if not state_counts.get(state)]
    return {"state_races": state_counts, "weekday_races": dict(sorted(weekdays.items())),
            "missing_states": missing_states,
            "meeting_grade_status": "MISSING" if not _has_meeting_grade(store) else "AVAILABLE",
            "ready_for_national_class_priors": not missing_states and _has_meeting_grade(store),
            "required_before_activation": ["authorised results", "durable horse identity", "meeting grade",
                "official times", "carried weight", "runner age and sex", "source provenance"]}


def _has_meeting_grade(store: RacingStore) -> bool:
    return any("meeting_grade" in row[1].lower() for row in store.connection.execute("PRAGMA table_info(race_results)"))
