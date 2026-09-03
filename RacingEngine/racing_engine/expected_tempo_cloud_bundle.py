"""Export the compact, non-secret Expected Tempo bundle used by cloud polling."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from .expected_tempo_dataset import PACE_VERSION, _going_bucket
from .expected_tempo_targets import rail_bucket, robust_location_scale
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_VERSION = "expected-tempo-cloud-bundle-v1"
LABELS = ["even", "fast", "slow", "very_fast_or_collapse"]


def key(*parts) -> str:
    return "|".join("missing" if value is None else str(value) for value in parts)


def build_bundle(store: RacingStore, targets_path: Path) -> dict:
    targets = pd.read_csv(targets_path)
    global_counts = Counter(targets["pace_label_4way"])
    contexts = {}
    targets["distance_band"] = (targets["distance_metres"] // 200 * 200).astype(int)
    targets["grade_key"] = targets["group_grade"].fillna("missing").astype(str)
    for values, group in targets.groupby(["state", "distance_band", "going_bucket", "grade_key"], dropna=False):
        contexts[key(*values)] = {
            "n": len(group), "label_counts": dict(Counter(group["pace_label_4way"])),
            "score_means": {phase: float(group[f"{phase}_score"].mean()) for phase in ("early", "middle", "late")},
        }
    rows = store.connection.execute(
        """SELECT r.source,r.track_slug,r.distance_metres,p.early_seconds,p.middle_seconds,p.late_seconds,
                  rr.track_condition,rr.rail_position
             FROM v2_clean_races r JOIN v2_race_pace_shapes p ON p.race_id=r.race_id AND p.version=?
             JOIN race_results rr ON rr.source=r.source AND rr.race_date=r.race_date
              AND rr.track_slug=r.track_slug AND rr.race_number=r.race_number
            WHERE p.early_seconds IS NOT NULL AND p.middle_seconds IS NOT NULL AND p.late_seconds IS NOT NULL""",
        (PACE_VERSION,),
    ).fetchall()
    groups = defaultdict(list)
    for row in rows:
        going = _going_bucket(row["track_condition"]); rail = rail_bucket(row["rail_position"])
        profile = "standard_3x400" if row["distance_metres"] >= 1200 else f"distance_{row['distance_metres']}"
        identities = {
            "track_distance_going_rail": key(row["source"], row["track_slug"], row["distance_metres"], going, rail),
            "track_distance_going": key(row["source"], row["track_slug"], row["distance_metres"], going),
            "track_phase_going": key(row["source"], row["track_slug"], profile, going),
            "source_distance_going": key(row["source"], row["distance_metres"], going),
            "source_phase_going": key(row["source"], profile, going),
            "track_distance": key(row["source"], row["track_slug"], row["distance_metres"]),
            "source_distance": key(row["source"], row["distance_metres"]),
            "source_phase": key(row["source"], profile),
        }
        for level, identity in identities.items():
            groups[(level, identity)].append(dict(row))
    pars = defaultdict(dict)
    for (level, identity), values in groups.items():
        if len(values) < 5:
            continue
        pars[level][identity] = {phase: dict(zip(("median", "scale"), robust_location_scale([float(row[f"{phase}_seconds"]) for row in values])))
                                 for phase in ("early", "middle", "late")}
        pars[level][identity]["n"] = len(values)
    return {
        "bundle_version": BUNDLE_VERSION, "source_pace_version": PACE_VERSION,
        "labels": LABELS, "global": {
            "n": len(targets), "label_counts": dict(global_counts),
            "score_means": {phase: float(targets[f"{phase}_score"].mean()) for phase in ("early", "middle", "late")},
        },
        "contexts": contexts, "pars": dict(pars),
        "policy": {"horse_price_integration": False, "probability_live_update": "held_until_prospective_gate"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--database", type=Path, default=ROOT/"data"/"racing_engine.sqlite")
    parser.add_argument("--targets", type=Path, default=ROOT/"reports"/"expected_tempo"/"expected_tempo_step2_targets.csv")
    parser.add_argument("--output", type=Path, default=ROOT.parent/"cloud"/"tempo_model_bundle.json")
    args = parser.parse_args(); store = RacingStore(args.database)
    try: bundle = build_bundle(store, args.targets)
    finally: store.close()
    args.output.write_text(json.dumps(bundle, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"output":str(args.output),"contexts":len(bundle["contexts"]),"par_cells":sum(map(len,bundle["pars"].values()))},indent=2))


if __name__ == "__main__": main()
