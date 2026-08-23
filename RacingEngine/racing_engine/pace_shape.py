"""V2 shadow pace-shape and runner workload ratings from canonical identities.

The outputs interpret completed races.  They do not project today's pace and
do not alter the accepted horse rating.  Positive pace scores mean faster than
the relevant historical par; positive shadow adjustments mean the runner was
estimated to have been disadvantaged by the observed shape.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .performance import going_bucket
from .storage import RacingStore, utc_now

ROOT = Path(__file__).resolve().parents[1]
VERSION = "pace-shape-v2.1-pit-shadow"
FEATURE_VERSION = "canonical-sectionals-v1.0"
SOURCES = {"racing-com-nsw-authorised-v2", "racing-com-rv-authorised"}


def schema(store: RacingStore) -> None:
    store.connection.executescript("""
    CREATE TABLE IF NOT EXISTS v2_sectional_quarantine (
      version TEXT NOT NULL, race_id TEXT NOT NULL, runner_number INTEGER,
      reason TEXT NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(version,race_id,runner_number,reason)
    );
    CREATE TABLE IF NOT EXISTS v2_race_pace_shapes (
      version TEXT NOT NULL, race_id TEXT NOT NULL, sectional_runners INTEGER NOT NULL,
      finished_runners INTEGER NOT NULL, coverage REAL NOT NULL,
      early_seconds REAL, middle_seconds REAL, late_seconds REAL,
      early_score REAL, middle_score REAL, late_score REAL,
      acceleration_score REAL, leader_pressure REAL, field_compression REAL,
      pace_label TEXT NOT NULL, confidence REAL NOT NULL, detail_json TEXT NOT NULL,
      created_at TEXT NOT NULL, PRIMARY KEY(version,race_id)
    );
    CREATE TABLE IF NOT EXISTS v2_runner_pace_ratings (
      version TEXT NOT NULL, race_id TEXT NOT NULL, runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL, horse_name TEXT NOT NULL,
      early_seconds REAL, middle_seconds REAL, late_seconds REAL,
      early_relative REAL, middle_relative REAL, late_relative REAL,
      early_contribution REAL, pressure_absorbed REAL, position_change REAL,
      pace_advantage REAL, shadow_rating_adjustment REAL,
      confidence REAL NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(version,race_id,runner_number)
    );
    CREATE TABLE IF NOT EXISTS v2_race_environments (
      version TEXT NOT NULL, race_id TEXT NOT NULL, weather_source TEXT,
      observed_at TEXT, temperature_c REAL, humidity_pct REAL,
      precipitation_mm REAL, wind_direction_deg REAL, wind_speed_kmh REAL,
      headwind_component_kmh REAL, crosswind_component_kmh REAL,
      steward_report_available INTEGER NOT NULL, steward_events INTEGER NOT NULL,
      lane_report_available INTEGER NOT NULL, environment_status TEXT NOT NULL,
      detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(version,race_id)
    );
    """)


def _median_scale(values: list[float]) -> tuple[float, float]:
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    # A tenth of a second prevents almost-identical electronic splits from
    # producing enormous standardised values.
    return median, max(0.10, 1.4826 * mad)


def _z_fast(value: float | None, median: float, scale: float) -> float | None:
    return max(-4.0, min(4.0, (median - value) / scale)) if value is not None else None


def _phase_times(source: str, distance: int, rows: list[Any]) -> tuple[float | None, float | None, float | None, list[str]]:
    by_marker = {int(row["marker_metres"]): float(row["section_seconds"]) for row in rows if row["section_seconds"] is not None}
    reasons: list[str] = []
    if source == "racing-com-rv-authorised":
        phases = (by_marker.get(800), by_marker.get(400), by_marker.get(0))
    else:
        # NSW stores consecutive 200m interval durations ending at the
        # metres-remaining marker.  Sum them into source-comparable phases.
        # The NSW report commonly supplies only the final 1200m in longer
        # races.  Define its early window as 1200-to-800 rather than rejecting
        # an otherwise complete, source-documented sequence.
        observed_distance = min(distance, 1200)
        expected = list(range(max(0, observed_distance - 200), -1, -200))
        missing = [marker for marker in expected if marker not in by_marker]
        if missing:
            reasons.append("missing_expected_markers:" + ",".join(map(str, missing)))
        def total(high: int, low: int) -> float | None:
            markers = [marker for marker in expected if low <= marker < high]
            return sum(by_marker[marker] for marker in markers) if markers and all(marker in by_marker for marker in markers) else None
        phases = (total(observed_distance, 800), total(800, 400), total(400, 0))
    names = ("early", "middle", "late")
    for name, value in zip(names, phases):
        if value is None: reasons.append(f"missing_{name}")
        elif value <= 0: reasons.append(f"nonpositive_{name}")
    return (*phases, reasons)


def _label(early: float | None, middle: float | None, late: float | None) -> str:
    if early is None or late is None: return "incomplete"
    if early >= .75 and late <= -.75: return "pace_collapse"
    if early <= -.75 and late >= .75: return "sprint_home"
    if early >= .50 and (middle or 0) >= .35 and late >= 0: return "sustained_high_pressure"
    if early >= 1.25: return "very_fast_early"
    if early >= .50: return "fast_early"
    if early <= -1.25: return "very_slow_early"
    if early <= -.50: return "slow_early"
    return "even"


def _race_rows(store: RacingStore) -> list[Any]:
    return store.connection.execute(
        """SELECT * FROM v2_clean_races WHERE source IN (?,?)
             ORDER BY race_date,track_slug,race_number""", tuple(sorted(SOURCES))).fetchall()


def build(store: RacingStore, *, version: str = VERSION, min_par_races: int = 5) -> dict[str, Any]:
    schema(store)
    for table in ("v2_sectional_quarantine", "v2_runner_pace_ratings", "v2_race_pace_shapes", "v2_race_environments"):
        store.connection.execute(f"DELETE FROM {table} WHERE version=?", (version,))
    races = _race_rows(store); timestamp = utc_now(); raw_races=[]; quarantines=Counter(); environment_counts=Counter()
    # Materialise what is actually available.  Wind components stay null until
    # surveyed course/section bearings exist; lane reports stay explicitly
    # missing rather than being inferred from winners.
    for race in races:
        weather=store.connection.execute(
            """SELECT * FROM race_weather WHERE race_date=? AND track_slug=? AND race_number=?
               ORDER BY CASE WHEN source=? THEN 0 ELSE 1 END LIMIT 1""",
            (race["race_date"],race["track_slug"],race["race_number"],race["source"])).fetchone()
        report=store.connection.execute(
            "SELECT 1 FROM steward_reports WHERE race_date=? AND track_slug=? AND race_number=? LIMIT 1",
            (race["race_date"],race["track_slug"],race["race_number"])).fetchone()
        events=store.connection.execute(
            "SELECT count(*) FROM steward_events WHERE race_date=? AND track_slug=? AND race_number=?",
            (race["race_date"],race["track_slug"],race["race_number"])).fetchone()[0]
        status="weather_only" if weather else "missing_weather_and_lane"
        environment_counts[status]+=1
        detail={"wind_components":"blocked_until_course_section_bearings_are_sourced",
                "lane_report":"not_available","weather_match":"race identity; preferred selected result source"}
        store.connection.execute("INSERT INTO v2_race_environments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (version,race["race_id"],weather["weather_source"] if weather else None,weather["observed_at"] if weather else None,
             weather["temperature_c"] if weather else None,weather["humidity_pct"] if weather else None,
             weather["precipitation_mm"] if weather else None,weather["wind_direction_deg"] if weather else None,
             weather["wind_speed_kmh"] if weather else None,None,None,int(report is not None),int(events),0,status,
             json.dumps(detail,sort_keys=True),timestamp))
    # First construct source-semantic phases and race medians.
    for race in races:
        runners = store.connection.execute(
            """SELECT * FROM v2_clean_runner_results WHERE race_id=? AND result_status='finished'
               AND finish_position IS NOT NULL ORDER BY runner_number""", (race["race_id"],)).fetchall()
        parsed=[]
        for runner in runners:
            rows=store.connection.execute(
                """SELECT marker_metres,section_seconds,position_at_marker FROM runner_sectionals
                   WHERE source=? AND race_date=? AND track_slug=? AND race_number=? AND runner_number=?
                   ORDER BY marker_metres DESC""", (race["source"],race["race_date"],race["track_slug"],race["race_number"],runner["runner_number"])).fetchall()
            early,middle,late,reasons=_phase_times(race["source"],int(race["distance_metres"] or 0),rows)
            positions={int(row["marker_metres"]):row["position_at_marker"] for row in rows}
            if reasons:
                for reason in reasons:
                    store.connection.execute("INSERT OR IGNORE INTO v2_sectional_quarantine VALUES (?,?,?,?,?,?)",
                        (version,race["race_id"],runner["runner_number"],reason,json.dumps({"source":race["source"]}),timestamp))
                    quarantines[reason.split(":",1)[0]]+=1
            if all(value is not None for value in (early,middle,late)):
                parsed.append({"runner":runner,"early":early,"middle":middle,"late":late,
                    "position_800":positions.get(800),"position_400":positions.get(400)})
        if len(parsed) < 3: continue
        phase_medians={phase:statistics.median(row[phase] for row in parsed) for phase in ("early","middle","late")}
        raw_races.append({"race":race,"runners":runners,"parsed":parsed,"medians":phase_medians})

    # Attach comparison keys, but do not populate the par samples yet.  Pars
    # are built while walking forward so a race can only see earlier races.
    for item in raw_races:
        race=item["race"]
        # v2 clean races currently do not persist going; recover it from the
        # selected official source without changing the accepted clean schema.
        condition=store.connection.execute("""SELECT track_condition FROM race_results WHERE source=? AND race_date=?
            AND track_slug=? AND race_number=?""",(race["source"],race["race_date"],race["track_slug"],race["race_number"])).fetchone()
        going=going_bucket(condition[0] if condition else None); item["going"]=going
        item["par_key"]=(race["source"],race["track_slug"],race["distance_metres"],going)
        item["fallback_key"]=(race["source"],race["distance_metres"],going)

    labels=Counter(); built_runners=0; exact_history:dict[tuple,list[dict]]=defaultdict(list); fallback_history:dict[tuple,list[dict]]=defaultdict(list)
    for item in raw_races:
        race=item["race"]; key=item["par_key"]; fallback=item["fallback_key"]
        exact=exact_history[key]; broad=fallback_history[fallback]
        sample=exact if len(exact)>=min_par_races else broad
        # Add the current race only after its score has been calculated.  Even
        # unscored seed races therefore become valid history for later races.
        if len(sample)<min_par_races:
            exact.append(item); broad.append(item); continue
        pars={};
        for phase in ("early","middle","late"):
            pars[phase]=_median_scale([row["medians"][phase] for row in sample])
        scores={phase:_z_fast(item["medians"][phase],*pars[phase]) for phase in pars}
        label=_label(scores["early"],scores["middle"],scores["late"]); labels[label]+=1
        coverage=len(item["parsed"])/len(item["runners"]); confidence=min(.95,.35+.45*coverage+.15*min(1,len(sample)/20))
        positions_800=[row["position_800"] for row in item["parsed"] if row["position_800"]]
        positions_400=[row["position_400"] for row in item["parsed"] if row["position_400"]]
        compression=(statistics.pstdev(positions_800)-statistics.pstdev(positions_400)) if len(positions_800)>=3 and len(positions_400)>=3 else None
        leader_pressure=max(0.0,scores["early"] or 0)+max(0.0,scores["middle"] or 0)
        acceleration=(scores["late"] or 0)-(scores["early"] or 0)
        detail={"par_key":key if len(exact)>=min_par_races else fallback,"par_sample":len(sample),
                "par_method":"strictly_prior_races_only","par_cutoff_exclusive":race["race_date"],
                "scores_positive_means_faster":True,"environment_adjustment":"not yet available"}
        store.connection.execute("INSERT INTO v2_race_pace_shapes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (version,race["race_id"],len(item["parsed"]),len(item["runners"]),coverage,item["medians"]["early"],item["medians"]["middle"],item["medians"]["late"],
             scores["early"],scores["middle"],scores["late"],acceleration,leader_pressure,compression,label,confidence,json.dumps(detail,sort_keys=True),timestamp))
        field_mid=(len(item["runners"])+1)/2
        phase_scales={phase:_median_scale([row[phase] for row in item["parsed"]]) for phase in ("early","middle","late")}
        for row in item["parsed"]:
            rel={phase:_z_fast(row[phase],*phase_scales[phase]) for phase in phase_scales}
            p800=float(row["position_800"] or field_mid); p400=float(row["position_400"] or p800); finish=float(row["runner"]["finish_position"])
            leader=max(0.0,(field_mid-p800)/max(1.0,field_mid-1)); closer=max(0.0,(p800-field_mid)/max(1.0,len(item["runners"])-field_mid))
            early_contribution=leader*max(0.0,scores["early"] or 0)*max(0.0,rel["early"] or 0)
            pressure=early_contribution+leader*max(0.0,scores["middle"] or 0)
            advantage=0.0
            if label=="pace_collapse": advantage=closer-leader
            elif label=="sprint_home": advantage=leader-closer
            elif label in ("very_fast_early","fast_early"): advantage=.5*closer-.5*leader
            # Positive adjustment compensates disadvantage; cap this first
            # shadow candidate at two rating points.
            adjustment=max(-2.0,min(2.0,-advantage*1.5+pressure*.35))
            position_change=p800-finish
            runner_conf=confidence*(1.0 if row["position_800"] and row["position_400"] else .8)
            runner_detail={"pace_label":label,"advantage_positive_means_helped":True,
                "adjustment_status":"shadow_not_in_official_rating","position_800":row["position_800"],"position_400":row["position_400"],"finish":finish}
            store.connection.execute("INSERT INTO v2_runner_pace_ratings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (version,race["race_id"],row["runner"]["runner_number"],row["runner"]["horse_key"],row["runner"]["horse_name"],row["early"],row["middle"],row["late"],
                 rel["early"],rel["middle"],rel["late"],early_contribution,pressure,position_change,advantage,adjustment,runner_conf,json.dumps(runner_detail,sort_keys=True),timestamp))
            built_runners+=1
        exact.append(item); broad.append(item)
    store.connection.commit()
    return {"version":version,"eligible_phase_complete_races":len(raw_races),"built_races":sum(labels.values()),"built_runners":built_runners,
            "pace_labels":dict(labels),"quarantine":dict(quarantines),"environment":dict(environment_counts),
            "rating_integration":"shadow only"}


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");parser.add_argument("--output",type=Path)
    args=parser.parse_args();store=RacingStore(args.database)
    try: report=build(store)
    finally: store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(rendered)
    else: print(rendered,end="")


if __name__=="__main__":main()
