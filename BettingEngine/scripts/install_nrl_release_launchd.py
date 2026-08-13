#!/usr/bin/env python3
"""Install the active-engine NRL release schedule on macOS."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = "com.betmate.nrl-release"


def main() -> None:
    parser = argparse.ArgumentParser(description="Install macOS NRL pricing + Baz release schedule.")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    uid = str(os.getuid())

    if args.uninstall:
        subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(plist_path)], check=False)
        plist_path.unlink(missing_ok=True)
        return

    logs = ROOT / "logs" / "release"
    logs.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [str(ROOT / "scripts" / "run_nrl_release_macos.sh")],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": [
            {"Weekday": 1, "Hour": 19, "Minute": 3},  # Monday first release
            {"Weekday": 4, "Hour": 18, "Minute": 0},  # Thursday final release / refs
        ],
        "StandardOutPath": str(logs / "nrl_release.out.log"),
        "StandardErrorPath": str(logs / "nrl_release.err.log"),
        "RunAtLoad": False,
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
    }
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    with plist_path.open("wb") as fh:
        plistlib.dump(payload, fh)

    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(plist_path)], check=False)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)], check=True)
    print(f"Installed {LABEL}: Monday 19:03 and Thursday 18:00")


if __name__ == "__main__":
    main()
