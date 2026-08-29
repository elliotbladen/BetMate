#!/usr/bin/env python3
"""Install macOS launch jobs for injury/news refresh and line prediction."""

from __future__ import annotations

import argparse
import plistlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = Path.home() / "Library" / "LaunchAgents"
PYTHON = "/usr/local/bin/python3"


def plist(label: str, command: list[str], out: Path, schedule: dict) -> dict:
    return {
        "Label": label,
        "ProgramArguments": command,
        "WorkingDirectory": str(ROOT),
        "EnvironmentVariables": {"PATH": "/usr/local/bin:/usr/bin:/bin"},
        "StandardOutPath": str(out.with_suffix(".out.log")),
        "StandardErrorPath": str(out.with_suffix(".err.log")),
        **schedule,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()
    log_dir = ROOT / "logs" / "market_intelligence"
    log_dir.mkdir(parents=True, exist_ok=True)
    jobs = {
        "com.bettingengine.monday-intelligence": plist(
            "com.bettingengine.monday-intelligence",
            [PYTHON, str(ROOT / "scripts/line_mover/collect_monday_intelligence.py")],
            log_dir / "monday_intelligence",
            {"StartCalendarInterval": {"Weekday": 1, "Hour": 7, "Minute": 15}},
        ),
        "com.bettingengine.championship-player-snapshots": plist(
            "com.bettingengine.championship-player-snapshots",
            [PYTHON, "-m", "ml.football.player_layer.fetch_espn_match_snapshots"],
            log_dir / "championship_player_snapshots",
            {"StartInterval": 1800, "RunAtLoad": True},
        ),
        "com.betmate.market-intelligence-refresh": plist(
            "com.betmate.market-intelligence-refresh",
            [PYTHON, str(ROOT / "scripts/market_intelligence_refresh.py")],
            log_dir / "refresh",
            {"StartInterval": 3600, "RunAtLoad": True},
        ),
        "com.bettingengine.line-mover-nrl": plist(
            "com.bettingengine.line-mover-nrl",
            [PYTHON, str(ROOT / "scripts/line_mover/run_pipeline.py"), "--sport", "NRL", "--round", "0", "--season", "2026"],
            log_dir / "nrl_line_mover",
            {"StartCalendarInterval": {"Weekday": 2, "Hour": 16, "Minute": 5}},
        ),
        "com.bettingengine.line-mover-monday-nrl": plist(
            "com.bettingengine.line-mover-monday-nrl",
            [PYTHON, str(ROOT / "scripts/line_mover/run_pipeline.py"), "--sport", "NRL", "--round", "0", "--season", "2026", "--stage", "monday"],
            log_dir / "nrl_line_mover_monday",
            {"StartCalendarInterval": [
                {"Weekday": 1, "Hour": 8, "Minute": 15},
                {"Weekday": 1, "Hour": 13, "Minute": 15},
            ]},
        ),
        "com.bettingengine.line-mover-monday-afl": plist(
            "com.bettingengine.line-mover-monday-afl",
            [PYTHON, str(ROOT / "scripts/line_mover/run_pipeline.py"), "--sport", "AFL", "--round", "0", "--season", "2026", "--stage", "monday"],
            log_dir / "afl_line_mover_monday",
            {"StartCalendarInterval": [
                {"Weekday": 1, "Hour": 8, "Minute": 20},
                {"Weekday": 1, "Hour": 13, "Minute": 20},
            ]},
        ),
        "com.bettingengine.line-mover-afl": plist(
            "com.bettingengine.line-mover-afl",
            [PYTHON, str(ROOT / "scripts/line_mover/run_pipeline.py"), "--sport", "AFL", "--round", "0", "--season", "2026"],
            log_dir / "afl_line_mover",
            {"StartCalendarInterval": [
                {"Weekday": 4, "Hour": 18, "Minute": 25},
                {"Weekday": 4, "Hour": 19, "Minute": 5},
                {"Weekday": 5, "Hour": 9, "Minute": 5},
            ]},
        ),
        "com.bettingengine.line-mover-score": plist(
            "com.bettingengine.line-mover-score",
            [PYTHON, str(ROOT / "scripts/line_mover/run_pipeline.py"), "--sport", "AFL", "--round", "0", "--season", "2026", "--score-only"],
            log_dir / "score",
            {"StartCalendarInterval": {"Weekday": 2, "Hour": 10, "Minute": 0}},
        ),
    }
    AGENTS.mkdir(parents=True, exist_ok=True)
    for label, payload in jobs.items():
        path = AGENTS / f"{label}.plist"
        subprocess.run(["launchctl", "bootout", f"gui/{Path.home().stat().st_uid}", str(path)], check=False)
        if args.uninstall:
            path.unlink(missing_ok=True)
            print(f"Removed {path}")
            continue
        path.write_bytes(plistlib.dumps(payload))
        subprocess.run(["launchctl", "bootstrap", f"gui/{Path.home().stat().st_uid}", str(path)], check=True)
        print(f"Installed {path}")


if __name__ == "__main__":
    main()
