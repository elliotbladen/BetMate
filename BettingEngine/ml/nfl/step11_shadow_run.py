"""Weekly NFL shadow-run checkpoint; deliberately fail-closed and non-betting."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .step10_readiness import assess_readiness

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "ml/nfl/reports"


def run_checkpoint() -> dict:
    card, readiness = assess_readiness()
    now = datetime.now(timezone.utc)
    result = {
        "status": "shadow_checkpoint_blocked" if readiness["blockers"] else "shadow_checkpoint_ready",
        "run_at_utc": now.isoformat(), "games": len(card), "blockers": readiness["blockers"],
        "t1_paper_card": "available",
        "t2_t3_live_shadow": "unresolved" if "quarterback_review_incomplete" in readiness["blockers"] else "available",
        "t6_weather_shadow": "unresolved" if "stadium_coordinates_and_weather_capture_incomplete" in readiness["blockers"] else "available",
        "t8_t9_market_shadow": "unresolved" if "no_valid_timestamped_market_quotes" in readiness["blockers"] else "available",
        "betting_decision": "ABSTAIN", "staking_enabled": False, "thresholds_retuned": False,
    }
    path = REPORTS / f"step11_shadow_checkpoint_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    result["report"] = str(path.relative_to(ROOT))
    return result


if __name__ == "__main__":
    print(json.dumps(run_checkpoint(), indent=2))
