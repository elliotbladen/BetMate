"""Step 2 sectional adjustment recovery experiment.

This module leaves accepted ratings untouched.  It separates repeatable
sectional achievement from trip compensation, removes point-in-time condition
and meeting-wide speed residuals, and fits jurisdiction coefficients from zero.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .pace_shape import VERSION as PACE_VERSION
from .storage import RacingStore, utc_now
from .v2_ratings import MODEL_VERSION

ROOT=Path(__file__).resolve().parents[1]
VERSION="sectional-adjustment-v2.2-shadow"


def _median(values): return statistics.median(values) if values else 0.0
def _clip(value,low,high): return max(low,min(high,value))


def schema(store:RacingStore)->None:
    store.connection.executescript("""
    CREATE TABLE IF NOT EXISTS v2_runner_sectional_components (
      version TEXT NOT NULL,race_id TEXT NOT NULL,runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL,jurisdiction TEXT NOT NULL,
      condition_residual REAL NOT NULL,meeting_speed_residual REAL NOT NULL,
      adjusted_early_score REAL,adjusted_middle_score REAL,adjusted_late_score REAL,
      achievement_signal REAL NOT NULL,trip_signal REAL NOT NULL,steward_signal REAL NOT NULL,
      fitted_achievement_coefficient REAL NOT NULL,fitted_trip_coefficient REAL NOT NULL,
      fitted_steward_coefficient REAL NOT NULL,shadow_adjustment REAL NOT NULL,
      confidence REAL NOT NULL,detail_json TEXT NOT NULL,created_at TEXT NOT NULL,
      PRIMARY KEY(version,race_id,runner_number));
    """)


def _condition(row:Any)->str:
    value=(row["track_condition"] or "unknown").lower().replace(" ","")
    return value


def _base_rows(store:RacingStore)->list[dict[str,Any]]:
    rows=store.connection.execute("""SELECT r.race_id,r.race_date,r.track_slug,r.race_number,r.distance_metres,r.source,
      rr.track_condition,s.early_score,s.middle_score,s.late_score,s.confidence,s.pace_label
      FROM v2_race_pace_shapes s JOIN v2_clean_races r USING(race_id)
      LEFT JOIN race_results rr ON rr.source=r.source AND rr.race_date=r.race_date
        AND rr.track_slug=r.track_slug AND rr.race_number=r.race_number
      WHERE s.version=? ORDER BY r.race_date,r.track_slug,r.race_number""",(PACE_VERSION,)).fetchall()
    return [dict(row) for row in rows]


def derive_race_residuals(store:RacingStore)->dict[str,dict[str,Any]]:
    """Condition correction is prior-only; meeting correction is leave-one-race-out."""
    rows=_base_rows(store); history:dict[tuple,list[dict[str,Any]]]=defaultdict(list); staged=[]
    for row in rows:
        jurisdiction="NSW" if "nsw" in row["source"] else "VIC"
        condition=_condition(row); key=(jurisdiction,row["track_slug"],row["distance_metres"],condition)
        prior=history[key]
        corrections={phase:_median([x[phase] for x in prior[-30:] if x[phase] is not None]) if len(prior)>=5 else 0.0
                     for phase in ("early_score","middle_score","late_score")}
        centred={phase:(float(row[phase])-corrections[phase] if row[phase] is not None else None) for phase in corrections}
        item={**row,"jurisdiction":jurisdiction,"condition":condition,"corrections":corrections,"centred":centred,
              "condition_sample":len(prior)}
        staged.append(item); history[key].append(row)
    meetings:dict[tuple,list[dict[str,Any]]]=defaultdict(list)
    for item in staged: meetings[(item["race_date"],item["track_slug"])].append(item)
    output={}
    for item in staged:
        peers=[x for x in meetings[(item["race_date"],item["track_slug"])] if x["race_id"]!=item["race_id"]]
        peer_values=[float(value) for peer in peers for value in peer["centred"].values() if value is not None]
        meeting_residual=_median(peer_values) if len(peers)>=2 else 0.0
        adjusted={phase:(value-meeting_residual if value is not None else None) for phase,value in item["centred"].items()}
        output[item["race_id"]]={**item,"meeting_residual":meeting_residual,"adjusted":adjusted,"meeting_peer_races":len(peers)}
    return output


def _component_rows(store:RacingStore,races:dict[str,dict[str,Any]])->list[dict[str,Any]]:
    rows=store.connection.execute("""SELECT q.*,c.horse_key,c.finish_position,p.performance_rating
      FROM v2_runner_pace_ratings q JOIN v2_clean_runner_results c USING(race_id,runner_number)
      JOIN v2_run_performances p ON p.race_id=q.race_id AND p.runner_number=q.runner_number
      WHERE q.version=? AND p.model_version=? ORDER BY q.race_id,q.runner_number""",(PACE_VERSION,MODEL_VERSION)).fetchall()
    output=[]
    for row in rows:
        race=races[row["race_id"]]; rels=[float(row[x] or 0) for x in ("early_relative","middle_relative","late_relative")]
        # Achievement rewards repeatable speed across the run, with greater
        # weight on the late phase. It is deliberately independent of whether
        # the race shape helped the horse.
        achievement=.20*rels[0]+.30*rels[1]+.50*rels[2]
        # Recalculate compensation from the condition/meeting-adjusted race
        # shape. This prevents a uniformly slow or fast meeting from creating
        # artificial workload. Positions are official sectional positions.
        runner_detail=json.loads(row["detail_json"]); field_size=store.connection.execute(
          "SELECT count(*) FROM v2_clean_runner_results WHERE race_id=? AND result_status='finished'",(row["race_id"],)).fetchone()[0]
        field_mid=(field_size+1)/2; p800=float(runner_detail.get("position_800") or field_mid)
        leader=max(0.0,(field_mid-p800)/max(1.0,field_mid-1)); closer=max(0.0,(p800-field_mid)/max(1.0,field_size-field_mid))
        early_score=float(race["adjusted"]["early_score"] or 0); middle_score=float(race["adjusted"]["middle_score"] or 0); late_score=float(race["adjusted"]["late_score"] or 0)
        early_work=leader*max(0.0,early_score)*max(0.0,rels[0]); pressure=early_work+leader*max(0.0,middle_score)
        collapse=_clip((early_score-late_score)/2,0,2); sprint=_clip((late_score-early_score)/2,0,2)
        pace_help=(closer-leader)*collapse+(leader-closer)*sprint
        trip=.35*pressure-pace_help
        steward=store.connection.execute("""SELECT COALESCE(sum(e.suggested_trip_adjustment),0)
          FROM steward_events e JOIN v2_clean_races r ON r.race_id=? AND e.race_date=r.race_date
           AND e.track_slug=r.track_slug AND e.race_number=r.race_number WHERE e.horse_key=?
           AND e.category IN ('wide_no_cover','held_up','interference','severe_interference','slow_start')""",
          (row["race_id"],row["horse_key"])).fetchone()[0]
        output.append({"race":race,"race_id":row["race_id"],"runner_number":row["runner_number"],"horse_key":row["horse_key"],
          "horse_name":row["horse_name"],"performance":float(row["performance_rating"]),"finish_position":row["finish_position"],
          "achievement":_clip(achievement,-4,4),"trip":_clip(trip,-4,4),"steward":_clip(float(steward),0,4),
          "confidence":float(row["confidence"])})
    return output


def _training_pairs(rows:list[dict[str,Any]],cutoff="2025-01-01")->dict[str,list[tuple[dict[str,Any],float]]]:
    horses:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in rows: horses[row["horse_key"]].append(row)
    result:dict[str,list[tuple[dict[str,Any],float]]]=defaultdict(list)
    for runs in horses.values():
        runs.sort(key=lambda x:(x["race"]["race_date"],x["race_id"]))
        for current,nxt in zip(runs,runs[1:]):
            if current["race"]["race_date"]<cutoff:
                result[current["race"]["jurisdiction"]].append((current,nxt["performance"]-current["performance"]))
    return result


def fit_coefficients(rows:list[dict[str,Any]])->dict[str,dict[str,float]]:
    pairs=_training_pairs(rows); grid=[x/10 for x in range(0,16)]; fitted={}
    for jurisdiction,sample in pairs.items():
        best=None
        for achievement in grid:
          for trip in grid:
            for steward in (0,.25,.5,.75,1.0):
              errors=[abs(target-(achievement*row["achievement"]+trip*row["trip"]+steward*row["steward"])) for row,target in sample]
              objective=statistics.mean(errors)+.002*(achievement+trip+steward)
              candidate=(objective,achievement,trip,steward)
              if best is None or candidate<best: best=candidate
        fitted[jurisdiction]={"achievement":best[1],"trip":best[2],"steward":best[3],"training_pairs":len(sample),"training_mae_penalised":best[0]}
    return fitted


def build(store:RacingStore)->dict[str,Any]:
    schema(store); store.connection.execute("DELETE FROM v2_runner_sectional_components WHERE version=?",(VERSION,))
    races=derive_race_residuals(store); rows=_component_rows(store,races); coefficients=fit_coefficients(rows); now=utc_now()
    adjustments=[]
    for row in rows:
        fitted=coefficients[row["race"]["jurisdiction"]]
        adjustment=_clip(fitted["achievement"]*row["achievement"]+fitted["trip"]*row["trip"]+fitted["steward"]*row["steward"],-3,3)
        race=row["race"]; adjusted=race["adjusted"]
        detail={"status":"shadow_only","condition":race["condition"],"condition_sample":race["condition_sample"],
          "meeting_peer_races":race["meeting_peer_races"],"achievement_definition":"20% early + 30% middle + 50% late runner-relative speed",
          "trip_definition":"35% pressure absorbed minus pace advantage","coefficient_fit":"pre-2025 next-start MAE; nonnegative grid starting at zero"}
        condition_residual=statistics.mean(race["corrections"].values())
        store.connection.execute("INSERT INTO v2_runner_sectional_components VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (VERSION,row["race_id"],row["runner_number"],row["horse_key"],race["jurisdiction"],condition_residual,race["meeting_residual"],
           adjusted["early_score"],adjusted["middle_score"],adjusted["late_score"],row["achievement"],row["trip"],row["steward"],
           fitted["achievement"],fitted["trip"],fitted["steward"],adjustment,row["confidence"],json.dumps(detail,sort_keys=True),now))
        adjustments.append(adjustment)
    store.connection.commit()
    return {"version":VERSION,"pace_source":PACE_VERSION,"races":len(races),"runners":len(rows),"coefficients":coefficients,
      "adjustment":{"minimum":min(adjustments),"maximum":max(adjustments),"mean":statistics.mean(adjustments),
                    "nonzero":sum(abs(x)>1e-9 for x in adjustments)},"accepted_rating_changed":False}


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite"); parser.add_argument("--output",type=Path)
    args=parser.parse_args(); store=RacingStore(args.database)
    try: report=build(store)
    finally: store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered)
    else: print(rendered,end="")


if __name__=="__main__":main()
