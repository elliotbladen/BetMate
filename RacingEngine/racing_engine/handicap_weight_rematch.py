"""Calibrate handicap weight response against subsequent WFA rematches."""
from __future__ import annotations

import argparse,json,statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .achieved_run_breakout import MODEL_VERSION as PARENT_VERSION,ROOT,build as build_parent
from .storage import RacingStore

MODEL_VERSION="handicap-weight-rematch-v1"
TRAINING_CUTOFF="2025-01-01"
MAX_DAYS=365
GRID=tuple(value/20 for value in range(21))
NAMED={"shezaalibi","gringotts","tropicus"}


def is_handicap(text:str)->bool:
    value=(text or "").lower();return "handicap" in value or value.startswith("quality")


def is_level_weights(text:str)->bool:
    value=(text or "").lower();return "weight for age" in value or "set weight" in value


def predicted_gap(first:dict,second:dict,coefficient:float)->float:
    return ((first["rating"]-first["weight"])-(second["rating"]-second["weight"])
            +coefficient*(first["weight"]-second["weight"]))


def build_pairs(store:RacingStore)->list[dict[str,Any]]:
    races={row["race_id"]:dict(row) for row in store.connection.execute("SELECT * FROM v2_clean_races")}
    by_race=defaultdict(list);appearances=defaultdict(list)
    for row in store.connection.execute("""SELECT a.race_id,a.runner_number,a.horse_key,a.horse_name,
        a.achieved_rating,a.weight_component,c.finish_position FROM v2_achieved_run_candidates a
        JOIN v2_clean_runner_results c USING(race_id,runner_number) WHERE a.model_version=?""",(PARENT_VERSION,)):
        item={"horse_key":row["horse_key"],"horse_name":row["horse_name"],"rating":float(row["achieved_rating"]),
              "weight":float(row["weight_component"]),"finish_position":int(row["finish_position"]),
              "race_id":row["race_id"],"date":races[row["race_id"]]["race_date"]}
        by_race[row["race_id"]].append(item);appearances[row["horse_key"]].append(item)
    for history in appearances.values():history.sort(key=lambda item:(item["date"],item["race_id"]))
    pairs=[]
    for race_id,runners in by_race.items():
        race=races[race_id]
        if not is_handicap(race["race_class"]):continue
        for i,first in enumerate(runners):
            for second in runners[i+1:]:
                start=date.fromisoformat(race["race_date"]);follow=None
                second_by_race={x["race_id"]:x for x in appearances[second["horse_key"]]}
                for later_first in appearances[first["horse_key"]]:
                    later_race=races[later_first["race_id"]]
                    days=(date.fromisoformat(later_race["race_date"])-start).days
                    later_second=second_by_race.get(later_first["race_id"])
                    if 0<days<=MAX_DAYS and later_second and is_level_weights(later_race["race_class"]):
                        follow=(later_first,later_second,later_race,days);break
                if not follow or abs(first["weight"]-second["weight"])<1e-9:continue
                later_first,later_second,later_race,days=follow
                pairs.append({"handicap_race_id":race_id,"handicap_date":race["race_date"],
                    "class_family":race["class_family"],"distance_metres":race["distance_metres"],
                    "first":first,"second":second,"later_race_id":later_first["race_id"],
                    "later_date":later_race["race_date"],"days":days,
                    "later_gap":later_first["rating"]-later_second["rating"],
                    "named_excluded":first["horse_key"] in NAMED or second["horse_key"] in NAMED})
    return pairs


def evaluate(rows:list[dict],coefficient:float)->dict[str,Any]:
    residuals=[predicted_gap(row["first"],row["second"],coefficient)-row["later_gap"] for row in rows]
    return {"pairs":len(rows),"mae":statistics.mean(abs(x) for x in residuals) if residuals else None,
            "median_error":statistics.median(residuals) if residuals else None}


def run(store:RacingStore)->dict[str,Any]:
    existing=store.connection.execute("SELECT count(*) FROM v2_achieved_run_candidates WHERE model_version=?",
                                      (PARENT_VERSION,)).fetchone()[0]
    if existing<29000:build_parent(store)
    pairs=build_pairs(store)
    training=[row for row in pairs if row["handicap_date"]<TRAINING_CUTOFF and not row["named_excluded"]]
    validation=[row for row in pairs if row["handicap_date"]>=TRAINING_CUTOFF and not row["named_excluded"]]
    trials=[{"coefficient":c,**evaluate(training,c)} for c in GRID]
    selected=min(trials,key=lambda row:(row["mae"],row["coefficient"]));coefficient=selected["coefficient"]
    named=[]
    for row in pairs:
        keys={row["first"]["horse_key"],row["second"]["horse_key"]}
        if keys=={"shezaalibi","gringotts"} and row["handicap_date"]=="2026-04-04":
            named.append({"handicap_date":row["handicap_date"],"later_wfa_date":row["later_date"],
                "days":row["days"],"selected_coefficient":coefficient,
                "handicap_gap_at_selected":predicted_gap(row["first"],row["second"],coefficient),
                "later_wfa_gap":row["later_gap"],"first":row["first"],"second":row["second"],
                "coefficient_matching_later_gap":((row["later_gap"]-
                    predicted_gap(row["first"],row["second"],0.0)) /
                    (row["first"]["weight"]-row["second"]["weight"]))})
    segments={}
    definitions={"group_1":lambda row:row["class_family"]=="group_1",
                 "group_1_mile":lambda row:row["class_family"]=="group_1" and 1300<=int(row["distance_metres"] or 0)<1800}
    for name,predicate in definitions.items():
        segment_train=[row for row in training if predicate(row)];segment_valid=[row for row in validation if predicate(row)]
        segment_trials=[{"coefficient":c,**evaluate(segment_train,c)} for c in GRID]
        segment_selected=min(segment_trials,key=lambda row:(row["mae"],row["coefficient"])) if segment_train else None
        segments[name]={"selection":segment_selected,"validation":evaluate(segment_valid,segment_selected["coefficient"]) if segment_selected else None,
                        "validation_zero":evaluate(segment_valid,0.0),"validation_full":evaluate(segment_valid,1.0)}
    return {"model_version":MODEL_VERSION,"training_cutoff_exclusive":TRAINING_CUTOFF,
        "named_horses_excluded_from_fit":sorted(NAMED),"selection":selected,"trials":trials,
        "validation":evaluate(validation,coefficient),"validation_zero":evaluate(validation,0.0),
        "validation_full":evaluate(validation,1.0),"segments":segments,"all_pairs":len(pairs),"named_audit":named,
        "interpretation":"Retrospective collateral consistency; not proof of a deterministic equal-weight result."}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"handicap_weight_rematch_v1.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
