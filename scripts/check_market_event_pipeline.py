"""
scripts/check_market_event_pipeline.py

One-off health check for the market-event causal-tagging pipeline built
2026-07-03. Run manually, or via the "BetMate Market Event Pipeline Checkin"
scheduled task ~3 weeks after launch, to see whether:
  - the 7 reactive snapshot tasks + weekly rebuild task have actually been firing
  - the "unexplained" percentage in the tagged dataset has shrunk from the
    ~90% baseline recorded at launch
  - snapshot windows around causal events have gotten tighter now that
    reactive snapshots are live (vs the multi-hour windows in the backfill)

Writes a dated report to data/market_events/checkins/{date}.md
"""
from __future__ import annotations

import csv
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_UNEXPLAINED_PCT = 90.0
BASELINE_DATE = "2026-07-03"

REACTIVE_TASKS = [
    "BetMate Odds Snapshot - React NRL Injuries",
    "BetMate Odds Snapshot - React NRL Team News",
    "BetMate Odds Snapshot - React AFL Injuries",
    "BetMate Odds Snapshot - React Emotional Flags",
    "BetMate Odds Snapshot - React NRL Referees",
    "BetMate Odds Snapshot - React NRL Weekend Injuries",
    "BetMate Odds Snapshot - React AFL Weekend Injuries",
    "BetMate Market Event Pipeline",
]


def check_task_history() -> str:
    """Shell out to schtasks for last-run info on each reactive task."""
    import subprocess
    lines = ["## Task Scheduler status\n"]
    for name in REACTIVE_TASKS:
        try:
            out = subprocess.run(
                ["schtasks", "/query", "/tn", name, "/fo", "LIST", "/v"],
                capture_output=True, text=True, timeout=15,
            ).stdout
            last_run = next((l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("Last Run Time")), "unknown")
            last_result = next((l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("Last Result")), "unknown")
            lines.append(f"- **{name}**: last run `{last_run}`, result `{last_result}`")
        except Exception as exc:
            lines.append(f"- **{name}**: could not query ({exc})")
    return "\n".join(lines)


def check_tagged_dataset(season: int = 2026) -> str:
    path = ROOT / "data" / "odds_movements" / "tagged" / f"{season}_tagged.csv"
    if not path.exists():
        return "## Tagged dataset\n\nNo tagged CSV found -- weekly rebuild may not have run."

    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    if not rows:
        return "## Tagged dataset\n\nTagged CSV is empty."

    unexplained = sum(1 for r in rows if r["drivers"] == "unexplained")
    pct_unexplained = 100 * unexplained / len(rows)

    # window size in hours, for rows that DID get a driver (post-launch reactive
    # snapshots should show much tighter windows than the pre-launch backfill)
    window_hours = []
    for r in rows:
        try:
            f = datetime.fromisoformat(r["from_time"])
            t = datetime.fromisoformat(r["to_time"])
            window_hours.append((t - f).total_seconds() / 3600)
        except Exception:
            continue

    recent = [r for r in rows if r["to_time"] >= BASELINE_DATE]
    recent_windows = []
    for r in recent:
        try:
            f = datetime.fromisoformat(r["from_time"])
            t = datetime.fromisoformat(r["to_time"])
            recent_windows.append((t - f).total_seconds() / 3600)
        except Exception:
            continue

    lines = [
        "## Tagged dataset\n",
        f"- Total significant moves: {len(rows)}",
        f"- Unexplained: {unexplained} ({pct_unexplained:.1f}%) -- baseline at launch ({BASELINE_DATE}) was ~{BASELINE_UNEXPLAINED_PCT:.0f}%",
        f"- Median window (all-time): {statistics.median(window_hours):.1f}h" if window_hours else "- No window data",
        f"- Median window (moves since launch, {BASELINE_DATE} onward): {statistics.median(recent_windows):.1f}h" if recent_windows else f"- No moves recorded since {BASELINE_DATE} yet",
        f"- Moves since launch: {len(recent)}",
    ]
    return "\n".join(lines)


def check_pipeline_log() -> str:
    path = ROOT / "data" / "market_events" / "logs" / "pipeline.log"
    if not path.exists():
        return "## Pipeline log\n\nNo pipeline.log found -- weekly rebuild task may never have run."
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [l for l in lines if "Starting market event pipeline" in l]
    return (
        "## Pipeline log\n\n"
        f"- Total recorded runs: {len(starts)} (expect ~3 for a 3-week check-in, weekly cadence)\n"
        f"- Most recent entries:\n```\n" + "\n".join(lines[-10:]) + "\n```"
    )


def main():
    report = [
        f"# Market Event Pipeline Check-in -- {datetime.now(timezone.utc).date().isoformat()}\n",
        f"Baseline recorded at launch ({BASELINE_DATE}): ~{BASELINE_UNEXPLAINED_PCT:.0f}% unexplained, multi-hour backfill windows.\n",
        check_task_history(),
        "",
        check_pipeline_log(),
        "",
        check_tagged_dataset(),
    ]
    text = "\n".join(report)

    out_dir = ROOT / "data" / "market_events" / "checkins"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{datetime.now(timezone.utc).date().isoformat()}.md"
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
