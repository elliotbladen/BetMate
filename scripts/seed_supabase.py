"""
scripts/seed_supabase.py

One-time seed: pushes all current local JSON files to Supabase.
Run this once before deploying to Vercel.

Usage:
  uv run --with requests python scripts/seed_supabase.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib" / "scraper"))

# Load .env.local
env_file = ROOT / ".env.local"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from supabase_push import push  # noqa: E402

FILES = [
    ("afl_bvi",        ROOT / "data" / "afl" / "bvi" / "processed" / "latest-bvi.json"),
    ("afl_home_away",  ROOT / "data" / "afl" / "home-away" / "processed" / "latest-home-away.json"),
    ("nrl_fixture",    ROOT / "data" / "nrl" / "fixture" / "processed" / "latest-fixture.json"),
    ("team_news_nrl",  ROOT / "data" / "nrl" / "team-news" / "latest.json"),
    ("team_news_afl",  ROOT / "data" / "afl" / "team-news" / "latest.json"),
]

ok = 0
skip = 0
fail = 0

for key, path in FILES:
    if not path.exists():
        print(f"  SKIP  {key} — file not found: {path}")
        skip += 1
        continue
    data = json.loads(path.read_text(encoding="utf-8"))
    result = push(key, data)
    if result:
        print(f"  OK    {key}")
        ok += 1
    else:
        print(f"  FAIL  {key}")
        fail += 1

print(f"\nDone: {ok} pushed, {skip} skipped, {fail} failed")
if fail:
    sys.exit(1)
