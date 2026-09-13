#!/usr/bin/env python3
"""Pre-flight audit for the team-news collector.

Written because on 2026-09-12 the odds collector lost ELEVEN HOURS of collection to
three faults that each looked fine in isolation:

  1. get_all() paged with Range offsets and no ORDER BY, so rows were silently
     skipped and the "already seen" guard came back incomplete.
  2. ignore_duplicates was resolved against the PRIMARY KEY, so the composite UNIQUE
     raised 23505 instead of being ignored - the insert claimed idempotence and had
     none.
  3. A partial failure returned exit 1, which made the platform restart the
     container and eventually stop scheduling the cron entirely.

Every check below targets one of those, or a new way to make the same mistake. It
fails loudly and exits non-zero so it can gate a deploy.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "sources"))

FAILS: list[str] = []
PASSES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASSES if ok else FAILS).append(f"{name}{(' — ' + detail) if detail else ''}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")


# ── 1. on_conflict must EXACTLY match a unique constraint in the migration ──────
def audit_on_conflict() -> None:
    print("\n[1] on_conflict targets vs the migration's unique constraints")
    sql = (ROOT / "supabase/migrations/20260913_team_sheets_and_availability.sql").read_text()
    code = (HERE / "team_news_collector.py").read_text()

    constraints: set[frozenset[str]] = set()
    for m in re.finditer(r"unique\s*\(([^)]+)\)", sql, re.I):
        constraints.add(frozenset(c.strip() for c in m.group(1).split(",")))
    for m in re.finditer(r"create unique index[^(]+\(([^)]+)\)", sql, re.I):
        cols = m.group(1)
        if "(" in cols:                       # an expression index - unusable here
            check("no expression in a unique index", False,
                  "PostgREST cannot target coalesce()/lower() from an on_conflict list")
            continue
        constraints.add(frozenset(c.strip() for c in cols.split(",")))

    targets = re.findall(r'on_conflict="([^"]+)"', code)
    check("collector declares on_conflict on every ignore-duplicates insert",
          len(targets) == code.count("ignore_duplicates=True"),
          f"{len(targets)} targets for {code.count('ignore_duplicates=True')} inserts")
    for target in targets:
        cols = frozenset(c.strip() for c in target.split(","))
        check(f"on_conflict [{target}] matches a real constraint", cols in constraints,
              "" if cols in constraints else f"no constraint has exactly these columns")


# ── 2. Every column written must exist in the schema ────────────────────────────
def audit_columns() -> None:
    print("\n[2] every column the collector writes exists in the migration")
    sql = (ROOT / "supabase/migrations/20260913_team_sheets_and_availability.sql").read_text()
    import team_news_collector as c

    tables = {}
    for m in re.finditer(r"create table if not exists public\.(\w+)\s*\((.*?)\n\);", sql, re.S):
        cols = set()
        for line in m.group(2).split("\n"):
            line = line.strip()
            if not line or line.startswith("--") or line.startswith(("unique", "primary", "check")):
                continue
            cols.add(line.split()[0])
        tables[m.group(1)] = cols

    ratings, _ = c.load_ratings()
    # Force every window so the audit always has rows to inspect; without this it
    # silently passes whenever no fixture happens to be inside a capture window.
    original = dict(c.WINDOWS)
    c.WINDOWS["football"] = list(range(0, 4 * 24 * 60, 5))
    payload = c.collect_football(None, "test-run", ratings)
    c.WINDOWS.update(original)
    for table, rows in (("team_sheet_observations", payload["sheets"]),
                        ("player_availability_observations", payload["absences"])):
        if not rows:
            check(f"{table}: sample row produced", False, "collector returned nothing to check")
            continue
        unknown = set(rows[0]) - tables.get(table, set())
        check(f"{table}: no unknown columns", not unknown,
              f"not in schema: {sorted(unknown)}" if unknown else f"{len(rows[0])} columns verified")
    return payload


# ── 3. Fingerprints must be deterministic, or every run duplicates everything ───
def audit_fingerprints(payload) -> None:
    print("\n[3] fingerprint stability and within-batch uniqueness")
    import team_news_collector as c
    a = c.fingerprint("x", None, 3)
    b = c.fingerprint("x", None, 3)
    check("fingerprint is deterministic", a == b)
    check("fingerprint distinguishes different input", a != c.fingerprint("x", None, 4))

    for table, rows, keys in (
        ("team_sheet_observations", payload["sheets"],
         ("source_match_id", "side", "value_fingerprint")),
        ("player_availability_observations", payload["absences"],
         ("code", "team_name", "player_name", "source_match_id", "value_fingerprint")),
    ):
        seen = [tuple(r[k] for k in keys) for r in rows]
        dupes = len(seen) - len(set(seen))
        # A duplicate INSIDE one batch is fatal: on_conflict de-dupes against rows
        # already in the table, not against the batch being sent, so Postgres raises
        # "ON CONFLICT DO UPDATE command cannot affect row a second time".
        check(f"{table}: no duplicate keys within one batch", dupes == 0,
              f"{dupes} duplicates in {len(rows)} rows")


# ── 4. Capture windows must actually fire, and only once each ──────────────────
def audit_windows() -> None:
    print("\n[4] capture windows")
    import team_news_collector as c
    for kind, expected in (("football", 85), ("NFL", 100)):
        hits = [m for m in range(0, 5000) if c.due_window(m, kind)]
        names = {c.due_window(m, kind) for m in hits}
        check(f"{kind}: all {len(c.WINDOWS[kind])} windows reachable",
              len(names) == len(c.WINDOWS[kind]), f"reachable: {sorted(names)}")
        check(f"{kind}: T-{expected}m window fires", c.due_window(expected, kind) is not None)
        # Windows must not overlap, or one capture satisfies two and the other never runs.
        overlap = [m for m in hits if sum(abs(m - t) <= c.TOLERANCE_MINUTES
                                          for t in c.WINDOWS[kind]) > 1]
        check(f"{kind}: no overlapping windows", not overlap,
              f"minutes hitting two windows: {overlap[:5]}" if overlap else "")
    # The bracket must have one window strictly BEFORE the publication deadline and
    # one strictly AFTER, or it cannot measure the reveal.
    for kind, deadline in (("football", 75), ("NFL", 90)):
        short = [w for w in c.WINDOWS[kind] if w < 180]
        check(f"{kind}: bracket straddles the {deadline}-minute deadline",
              any(w > deadline for w in short) and any(w < deadline for w in short),
              f"windows {sorted(short)} around {deadline}")
        names = [c.window_name(w) for w in c.WINDOWS[kind]]
        check(f"{kind}: every window name is distinct", len(set(names)) == len(names),
              f"{names}")


# ── 5. The cron must never exit non-zero on a data failure ─────────────────────
def audit_exit_codes() -> None:
    print("\n[5] exit codes (a non-zero exit unschedules the cron)")
    r = subprocess.run([sys.executable, str(HERE / "team_news_collector.py"), "--dry-run"],
                       capture_output=True, text=True, timeout=600)
    check("dry run exits 0", r.returncode == 0, f"returncode {r.returncode}")
    env_broken = {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": "",
                  "NEXT_PUBLIC_SUPABASE_URL": "", "ODDS_COLLECTION_LIVE_ENABLED": "true"}
    import os
    r2 = subprocess.run([sys.executable, str(HERE / "team_news_collector.py")],
                        capture_output=True, text=True, timeout=600,
                        env={**os.environ, **env_broken})
    check("missing credentials still exits 0", r2.returncode == 0,
          f"returncode {r2.returncode}")


# ── 6. Ratings must be point-in-time and never silently absent ─────────────────
def audit_ratings() -> None:
    print("\n[6] rating stamping")
    import team_news_collector as c
    ratings, source = c.load_ratings()
    check("a rating file was found", bool(ratings), f"{len(ratings)} players from {source}")
    if ratings:
        sample = next(iter(ratings.values()))
        check("ratings carry rated_on (point-in-time)", "rated_on" in sample,
              f"rated_on={sample.get('rated_on')}")


if __name__ == "__main__":
    print("AUDIT: team-news collector\n" + "=" * 60)
    audit_on_conflict()
    payload = audit_columns()
    if payload:
        audit_fingerprints(payload)
    audit_windows()
    audit_ratings()
    audit_exit_codes()
    print("\n" + "=" * 60)
    print(f"{len(PASSES)} passed, {len(FAILS)} FAILED")
    for f in FAILS:
        print(f"  FAIL  {f}")
    sys.exit(1 if FAILS else 0)
