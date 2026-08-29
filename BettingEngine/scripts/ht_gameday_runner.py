#!/usr/bin/env python3
"""
scripts/ht_gameday_runner.py

Unattended game-day runner for the halftime deep-stats capture mandate.
Meant to be fired daily by launchd (one job per sport):

    python3 scripts/ht_gameday_runner.py --sport nrl
    python3 scripts/ht_gameday_runner.py --sport afl

Behaviour:
  1. Ask the fixture API (NRL draw API / Squiggle) for the CURRENT round.
  2. If no games kick off today (local time) -> exit quietly.
  3. Otherwise start the sport's HT poller (nrl_ht_live.py / afl_ht_live.py)
     for that round and keep it alive until last kickoff + 2.5h, then stop.

Every HT capture appends to the go-forward archive and dumps the raw
deep-stats snapshot. Append-only; a missed game day is unrecoverable data.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

_ROOT = Path(__file__).resolve().parents[1]

# Dependencies needed by the HT pollers
_DEPS = ["requests", "beautifulsoup4"]

# Prefer uv (handles deps automatically), fall back to venv python, then system
def _find_python() -> list[str]:
    uv = shutil.which("uv")
    if uv:
        with_flags = []
        for dep in _DEPS:
            with_flags.extend(["--with", dep])
        return [uv, "run", *with_flags, "python"]
    venv_py = _ROOT / ".venv" / "bin" / "python"
    if venv_py.exists():
        return [str(venv_py)]
    return [sys.executable]

PYTHON_CMD = _find_python()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json,*/*",
}

NRL_DRAW_CURRENT = "https://www.nrl.com/draw/data/?competition=111&season={season}"
SQUIGGLE_YEAR = "https://api.squiggle.com.au/?q=games;year={season}"

BUFFER_AFTER_LAST_KO = timedelta(hours=2, minutes=30)  # HT is ~1h after KO
HEARTBEAT_STALE_SECONDS = 180


def todays_nrl(season: int) -> tuple[int | None, list[datetime]]:
    """Current NRL round + today's local kickoff times."""
    d = requests.get(NRL_DRAW_CURRENT.format(season=season), headers=HEADERS, timeout=20).json()
    round_num = d.get("selectedRoundId")
    kos = []
    today = datetime.now().date()
    for f in d.get("fixtures", []):
        if f.get("type") != "Match":
            continue
        ko_raw = (f.get("clock") or {}).get("kickOffTimeLong")
        if not ko_raw:
            continue
        ko = datetime.fromisoformat(ko_raw.replace("Z", "+00:00")).astimezone()
        if ko.date() == today:
            kos.append(ko)
    return round_num, kos


def todays_afl(season: int) -> tuple[int | None, list[datetime]]:
    """AFL round + today's local kickoff times (Squiggle unixtime)."""
    games = requests.get(SQUIGGLE_YEAR.format(season=season), headers=HEADERS, timeout=20).json().get("games", [])
    today = datetime.now().date()
    kos, rounds = [], set()
    for g in games:
        ut = g.get("unixtime")
        if not ut:
            continue
        ko = datetime.fromtimestamp(ut, tz=timezone.utc).astimezone()
        if ko.date() == today:
            kos.append(ko)
            rounds.add(g.get("round"))
    round_num = min(rounds) if rounds else None
    return round_num, kos


def main():
    p = argparse.ArgumentParser(description="Unattended HT poller launcher")
    p.add_argument("--sport", choices=["nrl", "afl"], required=True)
    p.add_argument("--season", type=int, default=datetime.now().year)
    args = p.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] ht_gameday_runner --sport {args.sport} --season {args.season}")

    fixture_fn = todays_nrl if args.sport == "nrl" else todays_afl
    for attempt in range(1, 6):
        try:
            round_num, kos = fixture_fn(args.season)
            break
        except Exception as exc:
            print(f"Fixture API error (attempt {attempt}/5): {exc}")
            if attempt == 5:
                sys.exit(1)
            time.sleep(30)

    if not kos:
        print("No games today — exiting.")
        return
    if round_num is None:
        print("Games today but could not resolve round — exiting.")
        sys.exit(1)

    stop_at = max(kos) + BUFFER_AFTER_LAST_KO
    print(f"Round {round_num}: {len(kos)} game(s) today, "
          f"first KO {min(kos):%H:%M}, last KO {max(kos):%H:%M}, "
          f"poller stops {stop_at:%H:%M}")

    poller = _ROOT / "scripts" / f"{args.sport}_ht_live.py"
    heartbeat = _ROOT / "logs" / "halftime" / f"{args.sport}_poller.heartbeat"
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    poller_cmd = [*PYTHON_CMD, "-u", str(poller),
                  "--round", str(round_num), "--season", str(args.season),
                  "--heartbeat", str(heartbeat)]

    # Hold every relevant macOS power assertion for the life of the poller.
    # `-i` alone only blocks idle sleep and did not prevent battery/maintenance
    # sleep on 2026-08-14. The lid still has to remain open.
    caffeinate = shutil.which("caffeinate")
    if caffeinate:
        cmd = [caffeinate, "-dimsu", "--", *poller_cmd]
        print("Using caffeinate -dimsu to prevent system, idle and display sleep")
    else:
        cmd = poller_cmd
        print(f"WARNING: caffeinate not found — Mac may sleep during games")

    def start_poller() -> subprocess.Popen:
        heartbeat.touch()
        return subprocess.Popen(cmd, cwd=str(_ROOT))

    proc = start_poller()
    try:
        while datetime.now().astimezone() < stop_at:
            if proc.poll() is not None:
                print(f"Poller exited early (code {proc.returncode}) — restarting.")
                proc = start_poller()
            else:
                try:
                    heartbeat_age = time.time() - heartbeat.stat().st_mtime
                except OSError:
                    heartbeat_age = HEARTBEAT_STALE_SECONDS + 1
                if heartbeat_age > HEARTBEAT_STALE_SECONDS:
                    print(
                        f"Poller heartbeat stale for {heartbeat_age:.0f}s — "
                        "terminating and restarting."
                    )
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=10)
                    proc = start_poller()
            time.sleep(30)
    finally:
        if proc.poll() is None:
            proc.terminate()
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Done — poller stopped.")


if __name__ == "__main__":
    main()
