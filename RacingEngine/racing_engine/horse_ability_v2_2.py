"""Horse Ability V2.2 using separated V2.7 achieved-run evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .achieved_run_breakout import MODEL_VERSION as RUN_MODEL_VERSION, ROOT, build as build_runs
from .horse_ability_v2 import run as run_ability
from .storage import RacingStore

ABILITY_VERSION = "horse-ability-v2.2-separated-achievement-shadow"


def run(store: RacingStore, protocol_path: Path, as_of_date: str):
    build_runs(store)
    return run_ability(store, protocol_path, as_of_date,
        run_model_version=RUN_MODEL_VERSION, ability_version=ABILITY_VERSION,
        report_name="horse-ability-v2.2-separated-achievement")


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--as-of",default="2026-08-23")
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"horse_ability_v2_2_separated.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s,a.protocol,a.as_of)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
