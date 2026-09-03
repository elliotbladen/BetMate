"""UCL player/personnel shadow status and bounded feature contract.

The UCL implementation deliberately mirrors the shared EPL/EFL player layer:
availability and expected minutes are captured before kickoff, then compared
with the team-only price.  It remains diagnostic/shadow until a chronological
player-data backtest proves incremental value.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data/ucl/context/player_events.csv"
REPORT = ROOT / "ml/football/reports/ucl_player_shadow.json"

REQUIRED = {
    "event_id", "match_id", "club_id", "player_id", "role", "status",
    "expected_minutes_share", "announced_at_utc", "source",
    "source_published_at_utc", "cutoff_utc",
}


def run_status() -> dict:
    if not EVENTS.exists():
        return {
            "status": "ucl_player_shadow_data_pending",
            "events": 0,
            "mode": "shadow",
            "production_price_influence": False,
            "next_gate": "populate timestamped UCL player events and observed appearances",
        }
    rows = pd.read_csv(EVENTS)
    missing = sorted(REQUIRED - set(rows.columns))
    if missing:
        raise ValueError(f"UCL player event file missing columns: {', '.join(missing)}")
    return {
        "status": "ucl_player_shadow_ready",
        "events": len(rows),
        "matches": int(rows["match_id"].nunique()),
        "mode": "shadow",
        "production_price_influence": False,
        "leakage_rule": "cutoff_utc must be no later than kickoff and source publication must precede cutoff",
        "shared_architecture": "ml/football/player_layer/PLAYER_LAYER_BUILD_SPEC.md",
        "next_gate": "walk-forward residual test against team-only UCL baseline",
    }


def main() -> None:
    result = run_status()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
