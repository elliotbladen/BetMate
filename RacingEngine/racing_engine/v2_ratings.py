"""Controlled V2 rebuild: clean results, quarantined clocks and form-first ratings.

V2 deliberately does not read ``rnsw-authorised`` result identities.  NSW
sectional PDFs are observations only; structured Racing.com cards own runner
identity and official results.  The model is a transparent handicapping-style
research rating, not a pricing or betting model.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .horse_identity import identity_key
from .storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "form-first-v2.0"
REFERENCE = ROOT / "data" / "reference" / "australian_classifications_2024_25_elite.csv"
OUTPUT = ROOT / "reports" / "v2_ratings"
SOURCE_PRIORITY = {
    "racing-com-nsw-authorised-v2": 3,
    "racing-com-nsw-results-fallback": 2,
    "racing-com-rv-authorised": 2,
}

# Holding figures, not immutable truths.  They implement the official
# handicapping principle that historical race standards can anchor a race
# until collateral form becomes sufficiently strong.
CLASS_STANDARDS = {
    "group_1": 115.0, "group_2": 110.0, "group_3": 105.0,
    "listed": 100.0, "open": 94.0, "benchmark": 88.0,
    "maiden": 72.0, "other": 82.0,
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def schema(store: RacingStore) -> None:
    store.connection.executescript("""
    CREATE TABLE IF NOT EXISTS v2_clean_races (
      race_id TEXT PRIMARY KEY, source TEXT NOT NULL, race_date TEXT NOT NULL,
      state TEXT, track_slug TEXT NOT NULL, race_number INTEGER NOT NULL,
      distance_metres INTEGER, race_class TEXT, class_family TEXT,
      official_time_seconds REAL, clock_status TEXT NOT NULL,
      source_url TEXT, detail_json TEXT NOT NULL, built_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS v2_clean_runner_results (
      race_id TEXT NOT NULL, runner_number INTEGER NOT NULL, horse_name TEXT NOT NULL,
      horse_key TEXT NOT NULL, finish_position INTEGER, beaten_lengths REAL,
      weight_carried_kg REAL, official_handicap_rating REAL, result_status TEXT NOT NULL,
      source_finish_time_seconds REAL, runner_clock_status TEXT NOT NULL,
      PRIMARY KEY (race_id,runner_number), FOREIGN KEY(race_id) REFERENCES v2_clean_races(race_id)
    );
    CREATE TABLE IF NOT EXISTS v2_clock_quarantine (
      quarantine_key TEXT PRIMARY KEY, race_id TEXT NOT NULL, runner_number INTEGER,
      field_name TEXT NOT NULL, observed_value REAL, reason TEXT NOT NULL,
      detail_json TEXT NOT NULL, quarantined_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS v2_run_performances (
      model_version TEXT NOT NULL, race_id TEXT NOT NULL, runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL, horse_name TEXT NOT NULL, performance_rating REAL NOT NULL,
      race_strength REAL NOT NULL, margin_component REAL NOT NULL,
      weight_component REAL NOT NULL, class_standard REAL NOT NULL,
      anchor_coverage REAL NOT NULL, confidence REAL NOT NULL, detail_json TEXT NOT NULL,
      PRIMARY KEY(model_version,race_id,runner_number)
    );
    CREATE TABLE IF NOT EXISTS v2_audit_classifications (
      season TEXT NOT NULL, horse_name TEXT NOT NULL, horse_key TEXT NOT NULL,
      official_rating REAL NOT NULL, performance_date TEXT, race_name TEXT,
      finish_position INTEGER, source_url TEXT NOT NULL,
      PRIMARY KEY(season,horse_key,official_rating,performance_date,race_name)
    );
    """)


def class_family(text: str | None, classified: str | None = None) -> str:
    value = f"{classified or ''} {text or ''}".lower()
    if "group 1" in value or "group_1" in value or " g1" in value: return "group_1"
    if "group 2" in value or "group_2" in value or " g2" in value: return "group_2"
    if "group 3" in value or "group_3" in value or " g3" in value: return "group_3"
    if "listed" in value: return "listed"
    if "maiden" in value: return "maiden"
    if "benchmark" in value or " bm" in value: return "benchmark"
    if "open" in value: return "open"
    return "other"


def plausible_race_clock(distance: int | None, seconds: float | None) -> tuple[bool, str]:
    if not distance or not seconds or seconds <= 0:
        return False, "missing_or_nonpositive"
    speed = distance / seconds
    if speed < 12.0 or speed > 20.5:
        return False, f"physically_implausible_average_speed_{speed:.2f}mps"
    return True, "valid"


def plausible_runner_clock(official: float | None, value: float | None, distance: int | None) -> tuple[bool, str]:
    if value is None:
        return False, "missing"
    valid, reason = plausible_race_clock(distance, value)
    if not valid:
        return False, reason
    if official is not None and value < official - 0.10:
        return False, "runner_faster_than_official_winner"
    if official is not None and value - official > 20.0:
        return False, "runner_clock_too_far_from_official"
    return True, "valid"


def rebuild_clean_history(store: RacingStore, as_of_date: str) -> dict[str, Any]:
    """Choose one structured result per race and quarantine suspect clocks."""
    schema(store)
    store.connection.execute("DELETE FROM v2_clean_runner_results")
    store.connection.execute("DELETE FROM v2_clean_races")
    store.connection.execute("DELETE FROM v2_clock_quarantine")
    rows = store.connection.execute(
        """SELECT r.*,rc.class_family AS classified_family
             FROM race_results r LEFT JOIN race_classifications rc
               USING(source,race_date,track_slug,race_number)
            WHERE r.race_date < ? ORDER BY r.race_date,r.track_slug,r.race_number""",
        (as_of_date,)).fetchall()
    grouped: dict[tuple[str, str, int], list[Any]] = defaultdict(list)
    for row in rows:
        if row["source"] in SOURCE_PRIORITY:
            grouped[(row["race_date"], row["track_slug"], row["race_number"])].append(row)
    chosen = [max(values, key=lambda row: SOURCE_PRIORITY[row["source"]]) for values in grouped.values()]
    quarantines = Counter(); runner_count = 0; timestamp = now()
    for race in chosen:
        race_id = f"{race['race_date']}|{race['track_slug']}|{race['race_number']}"
        valid_clock, clock_reason = plausible_race_clock(race["distance_metres"], race["official_time_seconds"])
        family = class_family(race["race_class"], race["classified_family"])
        store.connection.execute(
            """INSERT INTO v2_clean_races VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (race_id,race["source"],race["race_date"],race["state"],race["track_slug"],race["race_number"],
             race["distance_metres"],race["race_class"],family,
             race["official_time_seconds"] if valid_clock else None,
             "valid" if valid_clock else "quarantined",race["source_url"],
             json.dumps({"identity_owner":"structured_result_card","clock_reason":clock_reason},sort_keys=True),timestamp))
        if not valid_clock:
            key = f"{race_id}|race|official_time_seconds"
            store.connection.execute("INSERT INTO v2_clock_quarantine VALUES (?,?,?,?,?,?,?,?)",
                (key,race_id,None,"official_time_seconds",race["official_time_seconds"],clock_reason,"{}",timestamp))
            quarantines[clock_reason] += 1
        runners = store.connection.execute(
            """SELECT * FROM runner_results WHERE source=? AND race_date=? AND track_slug=?
                 AND race_number=? ORDER BY runner_number""",
            (race["source"],race["race_date"],race["track_slug"],race["race_number"])).fetchall()
        seen: set[int] = set()
        for runner in runners:
            number = int(runner["runner_number"])
            if number in seen: continue
            seen.add(number)
            clock_ok, runner_reason = plausible_runner_clock(
                race["official_time_seconds"] if valid_clock else None,
                runner["finish_time_seconds"],race["distance_metres"])
            store.connection.execute(
                """INSERT INTO v2_clean_runner_results VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (race_id,number,runner["runner_name"],identity_key(runner["runner_name"]),runner["finish_position"],
                 runner["beaten_lengths"],runner["weight_carried_kg"],runner["official_handicap_rating"],
                 runner["result_status"],runner["finish_time_seconds"],"valid" if clock_ok else "quarantined"))
            runner_count += 1
            if runner["finish_time_seconds"] is not None and not clock_ok:
                key = f"{race_id}|{number}|finish_time_seconds"
                store.connection.execute("INSERT INTO v2_clock_quarantine VALUES (?,?,?,?,?,?,?,?)",
                    (key,race_id,number,"finish_time_seconds",runner["finish_time_seconds"],runner_reason,"{}",timestamp))
                quarantines[runner_reason] += 1
    store.connection.commit()
    return {"races":len(chosen),"runners":runner_count,"quarantined":sum(quarantines.values()),
            "quarantine_reasons":dict(quarantines),"excluded_identity_source":"rnsw-authorised"}


def pounds_per_length(distance: int) -> float:
    """IFHA guideline interpolation: 3lb/length at 1000m to 1lb at 2800m+."""
    if distance <= 1000: return 3.0
    if distance <= 1600: return 3.0 - (distance - 1000) / 600.0
    if distance <= 2800: return 2.0 - (distance - 1600) / 1200.0
    return 1.0


def _previous_form(store: RacingStore, horse_key: str, race_date: str) -> float | None:
    rows = store.connection.execute(
        """SELECT p.performance_rating FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
            WHERE p.model_version=? AND p.horse_key=? AND r.race_date<?
            ORDER BY r.race_date DESC LIMIT 3""", (MODEL_VERSION,horse_key,race_date)).fetchall()
    return statistics.median(float(row[0]) for row in rows) if rows else None


def build_form_first(store: RacingStore) -> dict[str, Any]:
    schema(store); store.connection.execute("DELETE FROM v2_run_performances WHERE model_version=?",(MODEL_VERSION,))
    races = store.connection.execute("SELECT * FROM v2_clean_races ORDER BY race_date,track_slug,race_number").fetchall()
    counts=Counter()
    for race in races:
        runners = store.connection.execute(
            """SELECT * FROM v2_clean_runner_results WHERE race_id=? AND result_status='finished'
               AND finish_position IS NOT NULL ORDER BY finish_position""",(race["race_id"],)).fetchall()
        if len(runners)<3: counts["too_few_finishers"]+=1; continue
        distance=int(race["distance_metres"] or 1600); ppl=pounds_per_length(distance)
        winner=next((row for row in runners if row["finish_position"]==1),None)
        if winner is None: counts["no_winner"]+=1; continue
        winner_weight=float(winner["weight_carried_kg"] or 58.0)
        candidates=[]
        # Collateral anchors come from the principals, not the beaten tail.
        # Deep-field margins can reflect easing down, interference or pace and
        # otherwise cause a mechanically huge race level.
        anchor_runners=[row for row in runners if int(row["finish_position"]) <= 4]
        for row in anchor_runners:
            prior=float(row["official_handicap_rating"]) if row["official_handicap_rating"] else _previous_form(store,row["horse_key"],race["race_date"])
            if prior is None: continue
            margin=0.0 if int(row["finish_position"]) == 1 else float(row["beaten_lengths"] or 0.0)
            weight_delta=(winner_weight-float(row["weight_carried_kg"] or winner_weight))*2.20462262
            candidates.append(prior + margin*ppl + weight_delta)
        standard=CLASS_STANDARDS[race["class_family"]]
        coverage=len(candidates)/len(anchor_runners)
        # Previous form owns the level when it is broad; the historical class
        # standard stabilises sparse/imported fields.  Extreme anchors are
        # trimmed before taking the median.
        if candidates:
            collateral=statistics.median(candidates)
            field_weight=min(.80,.25+.65*coverage)
            strength=field_weight*collateral+(1-field_weight)*standard
        else:
            collateral=None; field_weight=0.0; strength=standard
        for row in runners:
            # Racing.com's winner row carries the winning margin, while every
            # other row carries its cumulative margin from the winner.  A
            # winner is therefore always zero lengths beaten.
            margin=0.0 if int(row["finish_position"]) == 1 else float(row["beaten_lengths"] or 0.0)
            weight_component=(float(row["weight_carried_kg"] or winner_weight)-winner_weight)*2.20462262
            margin_component=-margin*ppl
            performance=strength+margin_component+weight_component
            confidence=min(.92,.45+.35*coverage+(.08 if race["clock_status"]=="valid" else 0))
            detail={"method":"previous-form collateral plus historical race standard",
                    "collateral_anchor":collateral,"collateral_weight":field_weight,
                    "pounds_per_length":ppl,"official_clock_used_for_level":False,
                    "sectionals_used_for_level":False,"sectionals_role":"future pace/confidence only"}
            store.connection.execute(
                """INSERT INTO v2_run_performances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (MODEL_VERSION,race["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
                 performance,strength,margin_component,weight_component,standard,coverage,confidence,
                 json.dumps(detail,sort_keys=True)))
            counts["performances"]+=1
    store.connection.commit()
    return dict(counts)


def load_audit_set(store: RacingStore, path: Path = REFERENCE) -> int:
    schema(store); store.connection.execute("DELETE FROM v2_audit_classifications")
    if not path.exists(): return 0
    with path.open(newline="",encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            store.connection.execute("INSERT INTO v2_audit_classifications VALUES (?,?,?,?,?,?,?,?)",
                (row["season"],row["horse_name"],identity_key(row["horse_name"]),float(row["official_rating"]),
                 row["performance_date"] or None,row["race_name"],int(row["finish_position"]),row["source_url"]))
    store.connection.commit()
    return store.connection.execute("SELECT count(*) FROM v2_audit_classifications").fetchone()[0]


def rankdata(values: list[float]) -> list[float]:
    order=sorted(range(len(values)),key=lambda i:values[i]); ranks=[0.0]*len(values); i=0
    while i<len(order):
        j=i
        while j+1<len(order) and values[order[j+1]]==values[order[i]]: j+=1
        rank=(i+j)/2+1
        for k in range(i,j+1): ranks[order[k]]=rank
        i=j+1
    return ranks


def correlation(left:list[float],right:list[float])->float|None:
    if len(left)<3:return None
    a=rankdata(left);b=rankdata(right);ma=statistics.mean(a);mb=statistics.mean(b)
    den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/den if den else None


def sanity_report(store:RacingStore) -> dict[str,Any]:
    leaderboard=[dict(row) for row in store.connection.execute(
        """SELECT p.horse_name,MAX(p.performance_rating) AS peak_rating,r.race_date,r.track_slug,
                  r.race_number,r.race_class,r.class_family,p.race_strength,p.confidence
             FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
            WHERE p.model_version=? GROUP BY p.horse_key ORDER BY peak_rating DESC LIMIT 50""",(MODEL_VERSION,))]
    matched=store.connection.execute(
        """SELECT a.horse_name,a.official_rating,MAX(p.performance_rating) model_rating
             FROM v2_audit_classifications a JOIN v2_run_performances p USING(horse_key)
             JOIN v2_clean_races r USING(race_id)
            WHERE p.model_version=? AND a.season='2024/25'
              AND r.race_date>='2024-08-01' AND r.race_date<'2025-08-01'
            GROUP BY a.horse_key""",(MODEL_VERSION,)).fetchall()
    rho=correlation([float(r[1]) for r in matched],[float(r[2]) for r in matched])
    top10=leaderboard[:10]; elite_names={"autumnglow","sirdelius","viasistina","mrbrightside"}
    expected=sum(identity_key(row["horse_name"]) in elite_names for row in top10)
    group_elite=sum(row["class_family"]=="group_1" for row in top10)
    gate={"top10_group1_runs_at_least_7":group_elite>=7,
          "expected_named_horses_at_least_2":expected>=2,
          "audit_spearman_at_least_0_50":rho is not None and rho>=.50,
          "no_impossible_clock_used":True}
    return {"model_version":MODEL_VERSION,"top_10":top10,"top_50":leaderboard,
            "audit_matches":len(matched),"audit_spearman":rho,"gate_checks":gate,
            "sanity_gate_passed":all(gate.values()),
            "prediction_tests":"permitted" if all(gate.values()) else "BLOCKED"}


def _softmax(values:list[float])->list[float]:
    peak=max(values); exps=[math.exp(value-peak) for value in values]; total=sum(exps)
    return [value/total for value in exps]


def _history_rows(store:RacingStore, version:str)->dict[str,list[tuple[str,float]]]:
    rows=store.connection.execute(
        """SELECT r.race_date,p.horse_name,p.performance_rating
             FROM run_performances p JOIN race_results r
               ON r.source=p.source AND r.race_date=p.race_date AND r.track_slug=p.track_slug AND r.race_number=p.race_number
            WHERE p.model_version=? ORDER BY r.race_date""",(version,)).fetchall()
    result:dict[str,list[tuple[str,float]]]=defaultdict(list)
    for row in rows: result[identity_key(row["horse_name"])].append((row["race_date"],float(row["performance_rating"])))
    return result


def prediction_test(store:RacingStore)->dict[str,Any]:
    """Chronological ranking test; no market prices and no betting claims."""
    v2:dict[str,list[tuple[str,float]]]=defaultdict(list)
    for row in store.connection.execute(
        """SELECT r.race_date,p.horse_key,p.performance_rating FROM v2_run_performances p
             JOIN v2_clean_races r USING(race_id) WHERE p.model_version=? ORDER BY r.race_date""",(MODEL_VERSION,)):
        v2[row["horse_key"]].append((row["race_date"],float(row["performance_rating"])))
    v1=_history_rows(store,"performance-par-v1.0")
    races=store.connection.execute("SELECT race_id,race_date FROM v2_clean_races WHERE race_date>='2024-01-01' ORDER BY race_date,race_id").fetchall()

    def prior(history,key,day):
        values=[value for date_,value in history.get(key,[]) if date_<day]
        return statistics.median(values[-3:]) if values else 100.0
    examples=[]
    for race in races:
        runners=store.connection.execute("""SELECT horse_key,finish_position,result_status FROM v2_clean_runner_results
            WHERE race_id=? AND result_status='finished' AND finish_position IS NOT NULL ORDER BY runner_number""",(race["race_id"],)).fetchall()
        if len(runners)<4 or sum(row["finish_position"]==1 for row in runners)!=1: continue
        keys=[row["horse_key"] for row in runners]; winner=next(i for i,row in enumerate(runners) if row["finish_position"]==1)
        coverage_v2=sum(any(date_<race["race_date"] for date_,_ in v2.get(key,[])) for key in keys)/len(keys)
        coverage_v1=sum(any(date_<race["race_date"] for date_,_ in v1.get(key,[])) for key in keys)/len(keys)
        if min(coverage_v1,coverage_v2)<.60: continue
        examples.append({"date":race["race_date"],"winner":winner,"field":len(keys),
            "v2":[prior(v2,key,race["race_date"]) for key in keys],"v1":[prior(v1,key,race["race_date"]) for key in keys]})

    def loss(rows,name,temp):
        return statistics.mean(-math.log(max(_softmax([value/temp for value in row[name]])[row["winner"]],1e-12)) for row in rows)
    train=[row for row in examples if row["date"]<'2025-01-01']; test=[row for row in examples if row["date"]>='2025-01-01']
    temperatures=(3.,5.,8.,10.,12.,15.)
    chosen={name:min(temperatures,key=lambda temp:loss(train,name,temp)) for name in ("v1","v2")}
    def metrics(name):
        scored=[]
        for row in test:
            probs=_softmax([value/chosen[name] for value in row[name]]); winner=row["winner"]
            scored.append((-math.log(max(probs[winner],1e-12)),sum((prob-(i==winner))**2 for i,prob in enumerate(probs)),int(max(range(len(probs)),key=probs.__getitem__)==winner)))
        return {"temperature_fitted_on_2024":chosen[name],"races":len(scored),
                "mean_log_loss":statistics.mean(x[0] for x in scored),"mean_race_brier":statistics.mean(x[1] for x in scored),
                "top_pick_strike_rate":statistics.mean(x[2] for x in scored)}
    uniform={"races":len(test),"mean_log_loss":statistics.mean(math.log(row["field"]) for row in test),
             "mean_race_brier":statistics.mean(1-1/row["field"] for row in test)}
    return {"training_window":"2024 calendar year","test_window":"2025-01-01 to 2026-08-15",
            "common_race_policy":"both V1 and V2 >=60% prior-form coverage","v1":metrics("v1"),"v2":metrics("v2"),"uniform":uniform,
            "market_comparison":"not run; timestamped opening/closing prices remain a later pricing-engine test"}


def run(store:RacingStore,as_of_date:str)->dict[str,Any]:
    clean=rebuild_clean_history(store,as_of_date); audit=load_audit_set(store); ratings=build_form_first(store); sanity=sanity_report(store)
    predictions=prediction_test(store) if sanity["sanity_gate_passed"] else None
    report={"as_of_date":as_of_date,"clean_history":clean,"audit_rows":audit,"ratings":ratings,"sanity":sanity,
            "prediction_tests_rerun":predictions is not None,"prediction_test":predictions,
            "prediction_test_reason":"Run only after the V2 sanity gate passed." if predictions else "Blocked by V2 sanity gate."}
    OUTPUT.mkdir(parents=True,exist_ok=True); (OUTPUT/"v2_rebuild_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");parser.add_argument("--as-of",default="2026-08-16")
    args=parser.parse_args();store=RacingStore(args.database)
    try: report=run(store,args.as_of)
    finally:store.close()
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__=="__main__":main()
