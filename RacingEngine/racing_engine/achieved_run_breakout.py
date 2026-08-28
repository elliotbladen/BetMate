"""V2.7 targeted separated achievement for independently flagged breakouts."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .achieved_run_collateral import MODEL_VERSION as V24_VERSION, ROOT, build as build_v24
from .achieved_run_recovery import audits
from .achieved_run_separated import MODEL_VERSION as V26_VERSION, build as build_v26
from .storage import RacingStore

MODEL_VERSION = "achieved-run-v2.7-breakout-separated-shadow"
MIN_MARGIN_LENGTHS = 3.0
MAX_PRIOR_STARTS = 8
MAX_OPPOSITION_RELIABILITY = 0.50


def eligible_breakout(*, finish_position: int, winning_margin: float,
                      prior_starts: int, opposition_reliability: float) -> bool:
    return (finish_position == 1 and winning_margin >= MIN_MARGIN_LENGTHS
            and prior_starts <= MAX_PRIOR_STARTS
            and opposition_reliability < MAX_OPPOSITION_RELIABILITY)


def build(store: RacingStore) -> dict[str, Any]:
    build_v24(store); build_v26(store)
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?",(MODEL_VERSION,))
    rows=store.connection.execute(
        """SELECT p.*,s.achieved_rating separated_rating,s.race_strength separated_strength,
                  s.winner_margin_component separated_winner_margin,s.detail_json separated_detail,
                  c.finish_position,c.beaten_lengths
             FROM v2_achieved_run_candidates p JOIN v2_achieved_run_candidates s USING(race_id,runner_number)
             JOIN v2_clean_runner_results c USING(race_id,runner_number)
            WHERE p.model_version=? AND s.model_version=?""",(V24_VERSION,V26_VERSION)).fetchall()
    counts=Counter()
    for row in rows:
        separated=json.loads(row["separated_detail"])
        flags=separated["breakout_flags"]
        use=eligible_breakout(finish_position=int(row["finish_position"]),
            winning_margin=float(row["beaten_lengths"] or 0.0),
            prior_starts=int(flags["winner_prior_starts"]),
            opposition_reliability=float(separated["opposition_reliability"]))
        detail={**json.loads(row["detail_json"]),"candidate_version":MODEL_VERSION,
                "separated_achievement_eligible":use,
                "separated_achievement_rules":{"minimum_winning_margin_lengths":MIN_MARGIN_LENGTHS,
                    "maximum_prior_starts":MAX_PRIOR_STARTS,
                    "maximum_opposition_reliability_exclusive":MAX_OPPOSITION_RELIABILITY},
                "separated_achievement_detail":separated if use else None}
        achieved=float(row["separated_rating"] if use else row["achieved_rating"])
        strength=float(row["separated_strength"] if use else row["race_strength"])
        winner_margin=float(row["separated_winner_margin"] if use else row["winner_margin_component"])
        store.connection.execute("""INSERT INTO v2_achieved_run_candidates VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MODEL_VERSION,row["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
             achieved,row["base_rating"],strength,row["base_race_strength"],winner_margin,
             row["beaten_margin_component"],row["weight_component"],row["time_variant_component"],
             row["sectional_component"],row["collateral_revision_component"],row["confidence"],
             json.dumps(detail,sort_keys=True)))
        counts["performances"]+=1;counts["separated_breakout_winners"]+=int(use)
    store.connection.commit()
    return {"model_version":MODEL_VERSION,**dict(counts)}


def run(store:RacingStore)->dict[str,Any]:
    built=build(store);checked=audits(store,MODEL_VERSION)
    return {"build":built,"audits":checked,
            "decision":"SHADOW_CONTINUE" if checked["partial_gate_passed"] else "REVISE",
            "accepted_ratings_changed":False}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"achieved_run_v2_7_breakout.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
