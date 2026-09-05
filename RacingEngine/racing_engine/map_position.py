"""Point-in-time, shadow-only map-position profiles and field simulation."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .ratings import horse_key
from .storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
VERSION = "map-position-shadow-v1"
SECTIONAL_VERSION = "canonical-sectionals-v1.1-early-recovery"
STATES = ("leader", "on_pace", "midfield", "backmarker")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_from_position(position: int | None, field_size: int) -> str | None:
    if position is None or field_size < 1:
        return None
    rank = int(position)
    if rank == 1:
        return "leader"
    if rank <= max(3, math.ceil(field_size * 0.25)):
        return "on_pace"
    if rank <= max(5, math.ceil(field_size * 0.70)):
        return "midfield"
    return "backmarker"


def smoothed_probabilities(counts: Counter[str], *, alpha: float = 1.0) -> dict[str, float]:
    total = sum(counts.values()) + alpha * len(STATES)
    return {state: (counts.get(state, 0) + alpha) / total for state in STATES}


def blend_context(base: dict[str, float], barrier: int | None, field_size: int,
                  slow_start_rate: float = 0.0, forward_intent: float = 0.0) -> dict[str, float]:
    """Small bounded contextual tilt; historical behaviour remains dominant."""
    scores = {state: math.log(max(base[state], 1e-9)) for state in STATES}
    if barrier is not None and field_size > 1:
        percentile = (barrier - 1) / (field_size - 1)
        scores["leader"] += 0.35 * (0.5 - percentile)
        scores["on_pace"] += 0.15 * (0.5 - percentile)
        scores["backmarker"] += 0.20 * (percentile - 0.5)
    scores["leader"] -= min(0.8, slow_start_rate)
    scores["backmarker"] += min(0.4, slow_start_rate * 0.5)
    scores["leader"] += max(-0.6, min(0.6, forward_intent))
    scores["on_pace"] += max(-0.3, min(0.3, forward_intent * 0.5))
    peak = max(scores.values())
    exp = {key: math.exp(value - peak) for key, value in scores.items()}
    denominator = sum(exp.values())
    return {key: value / denominator for key, value in exp.items()}


def ensure_schema(store: RacingStore) -> None:
    store.connection.executescript("""
    CREATE TABLE IF NOT EXISTS map_course_configurations(
      config_version TEXT NOT NULL, track_slug TEXT NOT NULL, course_variant TEXT NOT NULL,
      distance_metres INTEGER NOT NULL, turn_direction TEXT, first_turn_distance_metres REAL,
      straight_distance_metres REAL, rail_position_raw TEXT, verification_status TEXT NOT NULL,
      source_url TEXT, detail_json TEXT NOT NULL, verified_at TEXT,
      PRIMARY KEY(config_version,track_slug,course_variant,distance_metres,rail_position_raw));
    CREATE TABLE IF NOT EXISTS map_runner_history_features(
      model_version TEXT NOT NULL, source TEXT NOT NULL, race_date TEXT NOT NULL,
      track_slug TEXT NOT NULL, race_number INTEGER NOT NULL, runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL, horse_name TEXT NOT NULL, observed_state TEXT,
      observed_position INTEGER, field_size INTEGER NOT NULL, early_time_seconds REAL,
      early_time_origin TEXT, barrier INTEGER, slow_start_event INTEGER NOT NULL,
      forward_tactics_event INTEGER NOT NULL, back_tactics_event INTEGER NOT NULL,
      information_cutoff TEXT NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(model_version,source,race_date,track_slug,race_number,runner_number));
    CREATE TABLE IF NOT EXISTS map_runner_predictions(
      model_version TEXT NOT NULL, as_of TEXT NOT NULL, field_hash TEXT NOT NULL,
      source TEXT NOT NULL, race_date TEXT NOT NULL, track_slug TEXT NOT NULL,
      race_number INTEGER NOT NULL, runner_number INTEGER NOT NULL, horse_key TEXT NOT NULL,
      horse_name TEXT NOT NULL, barrier INTEGER, history_runs INTEGER NOT NULL,
      leader_probability REAL NOT NULL, on_pace_probability REAL NOT NULL,
      midfield_probability REAL NOT NULL, backmarker_probability REAL NOT NULL,
      expected_settling_rank REAL, wide_risk REAL, slow_start_probability REAL NOT NULL,
      confidence REAL NOT NULL, simulation_seed INTEGER NOT NULL,
      information_cutoff TEXT NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(model_version,as_of,source,race_date,track_slug,race_number,runner_number));
    CREATE TABLE IF NOT EXISTS map_evaluations(
      model_version TEXT NOT NULL, evaluation_id TEXT NOT NULL, cutoff_date TEXT NOT NULL,
      runners INTEGER NOT NULL, log_loss REAL, brier REAL, accuracy REAL,
      baseline_log_loss REAL, baseline_brier REAL, detail_json TEXT NOT NULL,
      created_at TEXT NOT NULL, PRIMARY KEY(model_version,evaluation_id));
    CREATE INDEX IF NOT EXISTS idx_map_history_horse_date
      ON map_runner_history_features(horse_key,race_date);
    """)
    store.connection.commit()


def build_history(store: RacingStore) -> dict[str, int]:
    ensure_schema(store)
    rows = store.connection.execute("""
      SELECT rr.*,race.distance_metres,
             cs.early_to_800_seconds,cs.position_800m,cs.position_600m,cs.position_400m,
             cs.derivation_json,
             (SELECT count(*) FROM runner_results f WHERE f.source=rr.source
               AND f.race_date=rr.race_date AND f.track_slug=rr.track_slug
               AND f.race_number=rr.race_number AND f.result_status='finished') field_size
      FROM runner_results rr
      JOIN race_results race ON race.source=rr.source AND race.race_date=rr.race_date
       AND race.track_slug=rr.track_slug AND race.race_number=rr.race_number
      LEFT JOIN canonical_sectionals cs ON cs.feature_version=? AND cs.source=rr.source
       AND cs.race_date=rr.race_date AND cs.track_slug=rr.track_slug
       AND cs.race_number=rr.race_number AND cs.runner_number=rr.runner_number
      WHERE rr.result_status='finished'
      ORDER BY rr.race_date,rr.track_slug,rr.race_number,rr.runner_number""", (SECTIONAL_VERSION,)).fetchall()
    created = now(); labelled = 0
    for row in rows:
        position = row["position_800m"] or row["position_600m"] or row["position_400m"]
        state = state_from_position(position, int(row["field_size"] or 0))
        labelled += int(state is not None)
        events = {e[0] for e in store.connection.execute(
            "SELECT category FROM steward_events WHERE race_date=? AND track_slug=? AND race_number=? AND horse_key=?",
            (row["race_date"], row["track_slug"], row["race_number"], horse_key(row["runner_name"]))).fetchall()}
        derivation = json.loads(row["derivation_json"] or "{}")
        origin = "derived_finish_minus_late" if (derivation.get("features", {}).get("early_to_800_seconds", {}).get("method")) else ("observed" if row["early_to_800_seconds"] is not None else "unavailable")
        detail = {"position_marker_priority": "800,600,400", "distance_metres": row["distance_metres"]}
        store.connection.execute("""INSERT OR REPLACE INTO map_runner_history_features VALUES
          (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
          VERSION,row["source"],row["race_date"],row["track_slug"],row["race_number"],row["runner_number"],
          horse_key(row["runner_name"]),row["runner_name"],state,position,int(row["field_size"] or 0),
          row["early_to_800_seconds"],origin,row["barrier"],int("slow_start" in events or "failed_to_muster" in events),
          int("change_tactics_forward" in events),int("change_tactics_back" in events),row["race_date"],
          json.dumps(detail,sort_keys=True),created))
    store.connection.commit()
    return {"rows": len(rows), "labelled": labelled}


@dataclass
class RunnerInput:
    number: int
    name: str
    barrier: int | None


def _profile(store: RacingStore, runner: RunnerInput, race_date: str) -> tuple[dict[str, float], int, float]:
    key = horse_key(runner.name)
    rows = store.connection.execute("""SELECT observed_state,slow_start_event
      FROM map_runner_history_features WHERE model_version=? AND horse_key=?
       AND race_date<? AND observed_state IS NOT NULL ORDER BY race_date DESC LIMIT 8""",
      (VERSION,key,race_date)).fetchall()
    counts = Counter(row["observed_state"] for row in rows)
    slow = sum(row["slow_start_event"] for row in rows) / len(rows) if rows else 0.0
    return smoothed_probabilities(counts), len(rows), slow


def simulate_field(probabilities: list[dict[str, float]], barriers: list[int | None],
                   iterations: int = 10_000, seed: int = 1) -> list[dict[str, float]]:
    rng = random.Random(seed); n = len(probabilities)
    rank_sums = [0.0] * n; wide = [0] * n; state_counts = [Counter() for _ in range(n)]
    state_score = {"leader": 0.0, "on_pace": 1.0, "midfield": 2.0, "backmarker": 3.0}
    for _ in range(iterations):
        draws = []
        for i, probs in enumerate(probabilities):
            u=rng.random(); cumulative=0.0; chosen=STATES[-1]
            for state in STATES:
                cumulative += probs[state]
                if u <= cumulative: chosen=state; break
            barrier_penalty = ((barriers[i] or (n+1)/2) / max(n,1)) * 0.08
            draws.append((state_score[chosen]+barrier_penalty+rng.gauss(0,0.22),i,chosen))
        draws.sort()
        for rank,(_,i,chosen) in enumerate(draws,1):
            rank_sums[i] += rank; state_counts[i][chosen] += 1
            if barriers[i] is not None and barriers[i] > max(3,math.ceil(n*0.65)) and rank <= math.ceil(n*0.4): wide[i] += 1
    return [{"expected_rank":rank_sums[i]/iterations,"wide_risk":wide[i]/iterations,
             **{state:state_counts[i][state]/iterations for state in STATES}} for i in range(n)]


def predict_field(store: RacingStore, *, source: str, race_date: str, track_slug: str,
                  race_number: int, runners: Iterable[RunnerInput], as_of: str,
                  iterations: int = 10_000) -> list[dict[str, Any]]:
    ensure_schema(store); field=list(runners); size=len(field)
    field_hash=hashlib.sha256(json.dumps([(r.number,r.name,r.barrier) for r in field]).encode()).hexdigest()
    seed=int(field_hash[:8],16); probs=[]; metadata=[]
    for runner in field:
        base,runs,slow=_profile(store,runner,race_date)
        adjusted=blend_context(base,runner.barrier,size,slow_start_rate=slow)
        probs.append(adjusted); metadata.append((runs,slow))
    simulations=simulate_field(probs,[r.barrier for r in field],iterations,seed)
    output=[]; created=now()
    for runner,p,sim,(runs,slow) in zip(field,probs,simulations,metadata):
        confidence=min(0.90,0.20+0.09*runs)
        detail={"status":"SHADOW_ONLY","probability_model":"recency-eight-dirichlet-context-v1","iterations":iterations}
        values=(VERSION,as_of,field_hash,source,race_date,track_slug,race_number,runner.number,
                horse_key(runner.name),runner.name,runner.barrier,runs,p["leader"],p["on_pace"],p["midfield"],
                p["backmarker"],sim["expected_rank"],sim["wide_risk"],slow,confidence,seed,as_of,json.dumps(detail,sort_keys=True),created)
        store.connection.execute("""INSERT OR REPLACE INTO map_runner_predictions VALUES
          (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",values)
        output.append({"runner_number":runner.number,"horse_name":runner.name,"barrier":runner.barrier,
                       "probabilities":p,"expected_rank":sim["expected_rank"],"wide_risk":sim["wide_risk"],
                       "slow_start_probability":slow,"confidence":confidence})
    store.connection.commit(); return output


def evaluate_history(store: RacingStore) -> dict[str, Any]:
    """Strict chronological runner-style test against a population baseline."""
    ensure_schema(store)
    rows=store.connection.execute("""SELECT horse_key,observed_state,race_date,track_slug
      FROM map_runner_history_features WHERE model_version=? AND observed_state IS NOT NULL
      ORDER BY race_date,track_slug,race_number,runner_number""",(VERSION,)).fetchall()
    histories=defaultdict(list); population=Counter(); metrics=[]
    for row in rows:
        prior=Counter(histories[row["horse_key"]][-8:])
        p=smoothed_probabilities(prior); base=smoothed_probabilities(population)
        actual=row["observed_state"]; idx=STATES.index(actual)
        metrics.append((-math.log(max(p[actual],1e-12)),sum((p[s]-(s==actual))**2 for s in STATES)/len(STATES),
                        max(p,key=p.get)==actual,-math.log(max(base[actual],1e-12)),
                        sum((base[s]-(s==actual))**2 for s in STATES)/len(STATES)))
        histories[row["horse_key"]].append(actual); population[actual]+=1
    n=len(metrics); report={"model_version":VERSION,"runners":n,
      "log_loss":sum(x[0] for x in metrics)/n,"brier":sum(x[1] for x in metrics)/n,
      "accuracy":sum(x[2] for x in metrics)/n,"baseline_log_loss":sum(x[3] for x in metrics)/n,
      "baseline_brier":sum(x[4] for x in metrics)/n,"status":"SHADOW_ONLY_DIAGNOSTIC"}
    evaluation_id="historical-pit-v1"
    store.connection.execute("INSERT OR REPLACE INTO map_evaluations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
      (VERSION,evaluation_id,max((r["race_date"] for r in rows),default=""),n,report["log_loss"],report["brier"],
       report["accuracy"],report["baseline_log_loss"],report["baseline_brier"],json.dumps(report,sort_keys=True),now()))
    store.connection.commit(); return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    parser.add_argument("--build-history",action="store_true")
    parser.add_argument("--evaluate",action="store_true")
    args=parser.parse_args(); store=RacingStore(args.database)
    try:
        result=build_history(store) if args.build_history else (evaluate_history(store) if args.evaluate else {"status":"ready","version":VERSION})
        print(json.dumps(result,indent=2))
    finally: store.close()

if __name__ == "__main__": main()
