"""Strictly prior going/rail/meeting-adjusted V2 race-time evidence."""
from __future__ import annotations

import argparse
import json
import re
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .storage import RacingStore, utc_now

ROOT = Path(__file__).resolve().parents[1]
VERSION = "race-time-context-v2.1-shadow"
MIN_PAR_RACES = 20
MIN_RAIL_RACES = 10
MIN_MEETING_RACES = 3


def going_bucket(value: str | None) -> str:
    text = (value or "").lower()
    for name in ("heavy", "soft", "good", "firm", "synthetic"):
        if name in text:
            return name
    return "unknown"


def rail_bucket(value: str | None) -> str:
    text = (value or "").lower().strip()
    if not text:
        return "unknown"
    if "true" in text or "inside" in text:
        return "true"
    match = re.search(r"(?:out\s*)?(\d+(?:\.\d+)?)\s*m", text)
    if match:
        metres = float(match.group(1))
        return "out_1_4m" if metres <= 4 else ("out_5_8m" if metres <= 8 else "out_9m_plus")
    return "other"


def median_mad(values: list[float]) -> tuple[float, float]:
    centre = statistics.median(values)
    return centre, statistics.median(abs(value-centre) for value in values)


def schema(store: RacingStore) -> None:
    store.connection.executescript("""
    CREATE TABLE IF NOT EXISTS v2_race_time_evidence (
      version TEXT NOT NULL, race_id TEXT NOT NULL, source TEXT NOT NULL,
      race_date TEXT NOT NULL, track_slug TEXT NOT NULL, distance_metres INTEGER NOT NULL,
      going_bucket TEXT NOT NULL, rail_bucket TEXT NOT NULL, official_time_seconds REAL NOT NULL,
      prior_par_seconds REAL NOT NULL, prior_mad_seconds REAL NOT NULL, par_sample INTEGER NOT NULL,
      par_level TEXT NOT NULL, rail_adjustment_seconds REAL NOT NULL, rail_sample INTEGER NOT NULL,
      meeting_variant_seconds REAL NOT NULL, meeting_sample INTEGER NOT NULL,
      adjusted_residual_seconds REAL NOT NULL, fast_mad_signal REAL NOT NULL,
      confidence REAL NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(version,race_id));""")


def build(store: RacingStore) -> dict[str, Any]:
    schema(store);store.connection.execute("DELETE FROM v2_race_time_evidence WHERE version=?",(VERSION,))
    races=store.connection.execute("""SELECT r.*,rr.track_condition,rr.rail_position,
      coalesce(r.official_time_seconds,obs.official_time_seconds) effective_time_seconds,
      CASE WHEN r.official_time_seconds IS NOT NULL THEN 'structured_clean_clock'
           ELSE 'rnsw_observation_clock' END clock_provenance
      FROM v2_clean_races r LEFT JOIN race_results rr ON rr.source=r.source AND rr.race_date=r.race_date
       AND rr.track_slug=r.track_slug AND rr.race_number=r.race_number
      LEFT JOIN (SELECT race_date,track_slug,race_number,max(official_time_seconds) official_time_seconds
                   FROM race_results WHERE source='rnsw-authorised' AND official_time_seconds IS NOT NULL
                  GROUP BY race_date,track_slug,race_number) obs
        ON obs.race_date=r.race_date AND obs.track_slug=r.track_slug AND obs.race_number=r.race_number
      WHERE (r.clock_status='valid' AND r.official_time_seconds IS NOT NULL)
         OR obs.official_time_seconds IS NOT NULL
      ORDER BY r.race_date,r.race_id""").fetchall()
    exact=defaultdict(list);broad=defaultdict(list);rail_residuals=defaultdict(list)
    prepared=[];counts=Counter()
    # First pass creates point-in-time pars and rail residuals. No later clock
    # can influence an earlier race.
    by_day=defaultdict(list)
    for race in races:by_day[(race["source"],race["race_date"],race["track_slug"])].append(race)
    for day_key in sorted(by_day,key=lambda x:x[1]):
      day=[]
      for race in by_day[day_key]:
        going=going_bucket(race["track_condition"]);rail=rail_bucket(race["rail_position"])
        context_source=race["state"] or race["source"]
        ekey=(context_source,race["track_slug"],int(race["distance_metres"]),going)
        bkey=(context_source,race["track_slug"],int(race["distance_metres"]))
        history=exact[ekey] if len(exact[ekey])>=MIN_PAR_RACES else broad[bkey]
        if len(history)<MIN_PAR_RACES:
          counts["insufficient_prior_par"]+=1;day.append((race,None));continue
        par,mad=median_mad(history);level="track_distance_going" if history is exact[ekey] else "track_distance_fallback"
        rkey=(*ekey,rail);rhist=rail_residuals[rkey]
        rail_adjust=statistics.median(rhist) if len(rhist)>=MIN_RAIL_RACES else 0.0
        day.append((race,{"going":going,"rail":rail,"ekey":ekey,"bkey":bkey,"rkey":rkey,
          "par":par,"mad":max(.10,mad),"par_sample":len(history),"level":level,
          "rail_adjust":rail_adjust,"rail_sample":len(rhist)}))
      # Meeting variant uses the other eligible races only. Each residual is
      # already relative to its own strictly-prior going/rail context.
      for race,item in day:
        if item is None:continue
        others=[]
        for other,context in day:
          if context is None or other["race_id"]==race["race_id"]:continue
          others.append(float(other["effective_time_seconds"])-context["par"]-context["rail_adjust"])
        meeting=statistics.median(others) if len(others)>=MIN_MEETING_RACES else 0.0
        residual=float(race["effective_time_seconds"])-item["par"]-item["rail_adjust"]-meeting
        signal=-residual/item["mad"]
        confidence=min(.95,.45+.25*min(1,item["par_sample"]/50)+.15*min(1,len(others)/8)+.10*min(1,item["rail_sample"]/20))
        prepared.append((race,item,meeting,len(others),residual,signal,confidence))
      # Add this whole day's observations only after scoring the day.
      for race,item in day:
        going=going_bucket(race["track_condition"]);rail=rail_bucket(race["rail_position"])
        context_source=race["state"] or race["source"]
        ekey=(context_source,race["track_slug"],int(race["distance_metres"]),going)
        bkey=(context_source,race["track_slug"],int(race["distance_metres"]))
        value=float(race["effective_time_seconds"]);exact[ekey].append(value);broad[bkey].append(value)
        # Rail residual uses the going-aware par when available, broad prior otherwise.
        if item is not None:rail_residuals[(*ekey,rail)].append(value-item["par"])
    now=utc_now()
    for race,item,meeting,meeting_n,residual,signal,confidence in prepared:
      detail={"strictly_prior":True,"same_day_added_after_scoring":True,
        "going_source":race["track_condition"],"rail_source":race["rail_position"],
        "clock_provenance":race["clock_provenance"],"identity_owner":race["source"],
        "rail_applied":item["rail_sample"]>=MIN_RAIL_RACES,
        "meeting_variant_leave_one_race_out":True,"thresholds":{"par":MIN_PAR_RACES,"rail":MIN_RAIL_RACES,"meeting":MIN_MEETING_RACES}}
      store.connection.execute("INSERT INTO v2_race_time_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
       (VERSION,race["race_id"],race["source"],race["race_date"],race["track_slug"],race["distance_metres"],
        item["going"],item["rail"],race["effective_time_seconds"],item["par"],item["mad"],item["par_sample"],item["level"],
        item["rail_adjust"],item["rail_sample"],meeting,meeting_n,residual,signal,confidence,json.dumps(detail,sort_keys=True),now))
      counts["built"]+=1;counts[f"par_{item['level']}"]+=1;counts["rail_applied"]+=int(item["rail_sample"]>=MIN_RAIL_RACES)
      counts[race["clock_provenance"]]+=1
    store.connection.commit();return {"version":VERSION,"valid_clock_races":len(races),**dict(counts),"accepted_rating_changed":False}


def audit(store:RacingStore)->dict[str,Any]:
    natural=store.connection.execute("SELECT * FROM v2_race_time_evidence WHERE version=? AND race_id=?",(VERSION,"2026-08-15|caulfield|6")).fetchone()
    rows=store.connection.execute("SELECT fast_mad_signal FROM v2_race_time_evidence WHERE version=? AND race_date<?",(VERSION,"2025-01-01")).fetchall()
    values=[float(x[0]) for x in rows]
    return {"natural_fling":dict(natural) if natural else None,"pre_2025_rows":len(values),
      "pre_2025_fast_signal_p75":sorted(values)[int(.75*len(values))] if values else None,
      "interpretation":"historical performance evidence only; not a live pre-race input"}


def evaluate(store: RacingStore) -> dict[str, Any]:
    raw=store.connection.execute("""SELECT p.horse_key,r.race_date,r.state,p.performance_rating,t.fast_mad_signal
      FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
      LEFT JOIN v2_race_time_evidence t ON t.version=? AND t.race_id=p.race_id
      WHERE p.model_version='form-first-v2.0' ORDER BY p.horse_key,r.race_date""",(VERSION,)).fetchall()
    horses=defaultdict(list)
    for row in raw:horses[row["horse_key"]].append(row)
    pairs=[]
    for runs in horses.values():
      for current,nxt in zip(runs,runs[1:]):
        if current["fast_mad_signal"] is None:continue
        pairs.append({"date":current["race_date"],"state":current["state"],
          "signal":max(-3,min(3,float(current["fast_mad_signal"]))),
          "target":float(nxt["performance_rating"])-float(current["performance_rating"])})
    train=[x for x in pairs if x["date"]<"2025-01-01"]
    test=[x for x in pairs if x["date"]>="2025-01-01"]
    trials=[]
    for coefficient in (x/10 for x in range(21)):
      mae=statistics.mean(abs(x["target"]-coefficient*x["signal"]) for x in train) if train else None
      trials.append({"coefficient":coefficient,"training_next_start_mae":mae})
    selected=min(trials,key=lambda x:(x["training_next_start_mae"],x["coefficient"])) if train else {"coefficient":0.0}
    coefficient=float(selected["coefficient"])
    def metrics(sample):
      differences=[abs(x["target"]-coefficient*x["signal"])-abs(x["target"]) for x in sample]
      mean=statistics.mean(differences) if differences else None
      interval=(mean-1.96*statistics.stdev(differences)/math.sqrt(len(differences)),
                mean+1.96*statistics.stdev(differences)/math.sqrt(len(differences))) if len(differences)>1 else (None,None)
      return {"pairs":len(sample),"base_mae":statistics.mean(abs(x["target"]) for x in sample) if sample else None,
        "candidate_mae":statistics.mean(abs(x["target"]-coefficient*x["signal"]) for x in sample) if sample else None,
        "candidate_minus_base_mae":mean,"paired_95_interval":{"lower":interval[0],"upper":interval[1]}}
    overall=metrics(test);jurisdiction={state:metrics([x for x in test if x["state"]==state]) for state in ("NSW","VIC")}
    next_gate=bool(overall["candidate_minus_base_mae"] is not None and overall["candidate_minus_base_mae"]<0
      and overall["paired_95_interval"]["upper"]<0 and all(jurisdiction[s]["candidate_minus_base_mae"] is not None
      and jurisdiction[s]["candidate_minus_base_mae"]<0 for s in jurisdiction))
    return {"fit":{"window":"before 2025-01-01","pairs":len(train),"selected_coefficient":coefficient,"trials":trials},
      "test":{"window":"2025 onward","overall":overall,"jurisdiction":jurisdiction},
      "gates":{"next_start_mae":next_gate,"race_ranking_log_loss":False},
      "decision":"NOT_PROMOTED" if not next_gate else "BLOCKED_RANKING_GATE",
      "ranking_note":"A race-level time residual is common to every runner in that race; ranking impact must be tested through point-in-time horse states, not same-race outcomes."}


def main()->None:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"race_time_context_v2_1.json");a=p.parse_args();s=RacingStore(a.database)
 try:r={"build":build(s),"audit":audit(s),"evaluation":evaluate(s)}
 finally:s.close()
 rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered);print(rendered,end="")
if __name__=="__main__":main()
