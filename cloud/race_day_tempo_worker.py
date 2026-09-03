#!/usr/bin/env python3
"""Always-on Sydney/Melbourne sectional collector and tempo shadow updater."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from odds_collector import Supabase, iso, parse_time, truthy, utcnow
from racing_engine.expected_tempo_targets import rail_bucket
from racing_engine.pace_shape import _phase_times
from racing_engine.racing_com import DATE_QUERY, QUERY, graphql_request
from racing_engine.rnsw import download_atc_sectional_pdf, parse_sectional_pdf


HERE = Path(__file__).resolve().parent
CONFIG = HERE / "tempo_collection_config.json"
SOURCE = {"VIC": "racing-com-rv-authorised", "NSW": "racing-com-nsw-authorised-v2"}
VENUE_SLUGS = {
    "royal randwick": "randwick", "randwick": "randwick", "rosehill gardens": "rosehill",
    "caulfield": "caulfield", "caulfield heath": "caulfield-heath", "flemington": "flemington",
    "moonee valley": "the-valley", "the valley": "the-valley",
    "sportsbet sandown hillside": "sportsbet-sandown-hillside",
    "sportsbet sandown lakeside": "sportsbet-sandown-lakeside",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def going_bucket(value: str | None) -> str | None:
    text = (value or "").lower()
    return next((name for name in ("firm", "good", "soft", "heavy", "synthetic") if name in text), None)


def group_grade(value: str | None) -> int | None:
    match = re.search(r"\b(?:GROUP|G)\s*([123])\b", (value or "").upper())
    return int(match.group(1)) if match else None


def distance_metres(value) -> int | None:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return int(digits) if digits else None


def centiseconds(value) -> float | None:
    try:
        return int(value) / 100 if value not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        return None


def meeting_key(day: str, state: str, slug: str) -> str:
    return f"{day}|{state}|{slug}"


def race_key(meeting: str, number: int) -> str:
    return f"{meeting}|R{number}"


def discover(day: str, config: dict) -> list[dict]:
    records = graphql_request(DATE_QUERY, {"date": day}).get("data", {}).get("GetMeetingByDate") or []
    output = []
    for record in records:
        state = record.get("state")
        venue = (record.get("venue") or "").lower()
        if state not in config["enabled_states"] or venue not in config["venues"].get(state, []):
            continue
        if record.get("isTrial") or record.get("isJumpOut"):
            continue
        slug = VENUE_SLUGS[venue]
        output.append({"race_date": day, "state": state, "venue": record["venue"], "track_slug": slug,
                       "source_meeting_id": str(record["id"]), "source_url": record.get("meetUrl")})
    return output


def fetch_card(meet_code: str) -> list[dict]:
    payload = graphql_request(QUERY, {"meetCode": meet_code})
    return payload.get("data", {}).get("getNoCacheRacesForMeet") or []


def card_is_active(card: list[dict], now: datetime, config: dict) -> bool:
    starts = [parse_time(race.get("time")) for race in card]
    starts = [stamp for stamp in starts if stamp]
    if not starts:
        return False
    lower = min(starts) - timedelta(minutes=int(config["active_window_minutes_before_first"]))
    upper = max(starts) + timedelta(minutes=int(config["active_window_minutes_after_last"]))
    return lower <= now <= upper


def v0(bundle: dict, state: str, distance: int | None, going: str | None, grade: int | None) -> tuple[dict, dict]:
    global_row = bundle["global"]
    identity = "|".join(map(str, (state, (distance or 0) // 200 * 200, going or "missing", grade if grade else "missing")))
    local = bundle["contexts"].get(identity, {"n": 0, "label_counts": {}, "score_means": global_row["score_means"]})
    n = int(local["n"]); weight = n / (n + 25.0)
    probabilities = {}
    total = global_row["n"] + len(bundle["labels"])
    for label in bundle["labels"]:
        global_probability = (global_row["label_counts"].get(label, 0) + 1) / total
        local_probability = (local["label_counts"].get(label, 0) + 1) / (n + len(bundle["labels"]))
        probabilities[label] = weight * local_probability + (1 - weight) * global_probability
    scores = {phase: weight * local["score_means"][phase] + (1 - weight) * global_row["score_means"][phase]
              for phase in ("early", "middle", "late")}
    return probabilities, scores


def _par_candidates(source: str, track: str, distance: int, going: str | None, rail: str | None):
    profile = "standard_3x400" if distance >= 1200 else f"distance_{distance}"
    key = lambda *parts: "|".join("missing" if value is None else str(value) for value in parts)
    return [
        ("track_distance_going_rail", key(source, track, distance, going, rail_bucket(rail))),
        ("track_distance_going", key(source, track, distance, going)),
        ("track_phase_going", key(source, track, profile, going)),
        ("source_distance_going", key(source, distance, going)),
        ("source_phase_going", key(source, profile, going)),
        ("track_distance", key(source, track, distance)),
        ("source_distance", key(source, distance)),
        ("source_phase", key(source, profile)),
    ]


def score_phases(bundle: dict, source: str, track: str, distance: int, going: str | None,
                 rail: str | None, phases: dict[str, float]) -> tuple[dict, str, int]:
    for level, identity in _par_candidates(source, track, distance, going, rail):
        par = bundle["pars"].get(level, {}).get(identity)
        if par:
            scores = {phase: max(-4.0, min(4.0, (par[phase]["median"] - phases[phase]) / par[phase]["scale"]))
                      for phase in phases}
            return scores, level, int(par["n"])
    raise ValueError("no deployment par for race context")


def victoria_observations(card: list[dict], state: str, slug: str, bundle: dict) -> list[dict]:
    output = []
    source = SOURCE[state]
    for race in card:
        parsed = []
        finishers = 0
        for entry in race.get("formRaceEntries") or []:
            if entry.get("position") in (None, 109):
                continue
            finishers += 1; timing = entry.get("timing") or {}
            phases = [centiseconds(timing.get(name)) for name in (
                "toEightHundredMetresSeconds", "eightHundredToFourHundredMetresSeconds", "fourHundredToFinishMetresSeconds")]
            if all(value is not None for value in phases):
                parsed.append(phases)
        if len(parsed) < 3:
            continue
        values = {phase: statistics.median(row[index] for row in parsed)
                  for index, phase in enumerate(("early", "middle", "late"))}
        meet = race.get("meet") or {}; distance = distance_metres(race.get("distance")); going = going_bucket(race.get("trackCondition") or meet.get("trackCondition"))
        scores, level, sample = score_phases(bundle, source, slug, distance, going, meet.get("railPosition"), values)
        output.append({"race_number": int(race["raceNumber"]), "distance_metres": distance,
                       "going_bucket": going, "rail_position": meet.get("railPosition"), "phases": values,
                       "scores": scores, "sectional_runners": len(parsed), "finished_runners": finishers,
                       "coverage": len(parsed)/finishers if finishers else 0, "par_level": level, "par_sample": sample,
                       "source_url": f"https://www.racing.com/form/{meet.get('date')}/{slug}"})
    return output


def sydney_observations(day: str, slug: str, bundle: dict) -> list[dict]:
    payload, url = download_atc_sectional_pdf(day, slug)
    parsed_races = parse_sectional_pdf(payload, day, slug, url); output = []
    source = SOURCE["NSW"]
    for race in parsed_races:
        phases_by_runner = []
        for runner in race["runners"]:
            phases = _phase_times(source, race["distance_metres"], runner["sectionals"])[0:3]
            if all(value is not None for value in phases): phases_by_runner.append(phases)
        if len(phases_by_runner) < 3: continue
        values = {phase: statistics.median(row[index] for row in phases_by_runner)
                  for index, phase in enumerate(("early", "middle", "late"))}
        going = going_bucket(race.get("track_condition")); rail = race.get("rail_position")
        scores, level, sample = score_phases(bundle, source, slug, race["distance_metres"], going, rail, values)
        output.append({"race_number": race["race_number"], "distance_metres": race["distance_metres"],
                       "going_bucket": going, "rail_position": rail, "phases": values, "scores": scores,
                       "sectional_runners": len(phases_by_runner), "finished_runners": len(race["runners"]),
                       "coverage": len(phases_by_runner)/len(race["runners"]), "par_level": level,
                       "par_sample": sample, "source_url": url})
    return output


def shadow_state(observations: list[dict], target: dict, cap: float) -> tuple[dict, float, int]:
    usable = []
    for row in observations:
        if row.get("going_bucket") != target.get("going_bucket"): continue
        distance_weight = math.exp(-abs(float(row["distance_metres"])-float(target["distance_metres"]))/600)
        gap = max(0, int(target["race_number"])-int(row["race_number"])-1)
        weight = distance_weight * math.exp(-0.18*gap) * max(0.25, float(row["coverage"]))
        usable.append((row, weight))
    total = sum(weight for _, weight in usable); reliability = total/(total+2) if total else 0
    state = {phase: reliability * sum(row["scores"][phase]*weight for row, weight in usable)/total if total else 0
             for phase in ("early", "middle", "late")}
    scores = dict(target["v0_scores"]); scores["early"] = target["v0_scores"]["early"]
    for phase in ("middle", "late"):
        scores[phase] += max(-cap, min(cap, state[phase]))
    return scores, reliability, len(usable)


def process_meeting(db: Supabase | None, meeting: dict, card: list[dict], bundle: dict, config: dict,
                    now: datetime, dry_run: bool, poll_sectionals: bool = True) -> dict:
    key = meeting_key(meeting["race_date"], meeting["state"], meeting["track_slug"])
    meeting_row = {"meeting_key": key, **meeting, "status": "live", "updated_at": iso(now)}
    race_rows = []
    for race in card:
        meet = race.get("meet") or {}; distance = distance_metres(race.get("distance")); going = going_bucket(race.get("trackCondition") or meet.get("trackCondition"))
        grade = group_grade(race.get("condition")); probabilities, scores = v0(bundle, meeting["state"], distance, going, grade)
        race_rows.append({"race_key": race_key(key, int(race["raceNumber"])), "meeting_key": key,
                          "race_number": int(race["raceNumber"]), "scheduled_start_at": race.get("time"),
                          "distance_metres": distance, "going_bucket": going, "rail_position": meet.get("railPosition"),
                          "group_grade": grade, "field_size": len(race.get("formRaceEntries") or []),
                          "v0_probabilities": probabilities, "v0_scores": scores,
                          "v0_model_version": bundle["bundle_version"], "status": "scheduled", "updated_at": iso(now)})
    if db: db.upsert("tempo_meetings", [meeting_row]); db.upsert("tempo_races", race_rows)
    observations = []
    if poll_sectionals:
        observations = (victoria_observations(card, meeting["state"], meeting["track_slug"], bundle)
                        if meeting["state"] == "VIC"
                        else sydney_observations(meeting["race_date"], meeting["track_slug"], bundle))
    accepted = [row for row in observations if row["coverage"] >= config["minimum_sectional_coverage"] and row["sectional_runners"] >= config["minimum_sectional_runners"]]
    observation_rows = []
    for row in accepted:
        identity = json.dumps(row, sort_keys=True); payload_hash = hashlib.sha256(identity.encode()).hexdigest()
        observation_rows.append({"race_key": race_key(key,row["race_number"]), "observed_at": iso(now),
            "source_name": SOURCE[meeting["state"]], "source_url": row["source_url"], "payload_sha256": payload_hash,
            "sectional_runners": row["sectional_runners"], "finished_runners": row["finished_runners"],
            "sectional_coverage": row["coverage"], **{f"{p}_seconds":row["phases"][p] for p in ("early","middle","late")},
            **{f"{p}_score":row["scores"][p] for p in ("early","middle","late")}, "quality_status":"accepted",
            "evidence":{"par_level":row["par_level"],"par_sample":row["par_sample"]}})
    if db: db.insert("tempo_race_observations", observation_rows, ignore_duplicates=True)
    snapshots = []
    for target in race_rows:
        prior = [row for row in accepted if row["race_number"] < target["race_number"]]
        scores, reliability, same_regime = shadow_state(prior, target, config["live_middle_late_cap"])
        status = "updated" if same_regime and reliability >= config["minimum_state_reliability"] else ("condition_reset" if prior else "v0")
        if status != "updated": scores = target["v0_scores"]
        detail = {"race_key":target["race_key"],"completed":len(prior),"same_regime":same_regime,
                  "v0":target["v0_scores"],"shadow":scores,"status":status,"bundle":bundle["bundle_version"]}
        snapshot_hash = hashlib.sha256(json.dumps(detail,sort_keys=True).encode()).hexdigest()
        snapshots.append({"snapshot_hash":snapshot_hash,"race_key":target["race_key"],"meeting_key":key,
            "snapshot_version":f"V{len(prior)}","calculated_at":iso(now),"completed_races":len(prior),
            "same_regime_races":same_regime,"state_reliability":reliability,"v0_probabilities":target["v0_probabilities"],
            "shadow_probabilities":target["v0_probabilities"],"v0_scores":target["v0_scores"],"shadow_scores":scores,
            "update_status":status,"reason_codes":["early_held_v0","probabilities_held_amber",status],
            "model_version":bundle["bundle_version"],"policy_version":"expected-tempo-shadow-policy-v1",
            "horse_price_integration":False,"detail":detail})
    if db: db.insert("tempo_shadow_snapshots", snapshots, ignore_duplicates=True)
    return {"meeting":key,"races":len(race_rows),"observations":len(observation_rows),"snapshots":len(snapshots),
            "poll_sectionals":poll_sectionals,"dry_run":dry_run}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--date"); parser.add_argument("--dry-run",action="store_true"); parser.add_argument("--force",action="store_true")
    args=parser.parse_args(); config=load_json(CONFIG); bundle=load_json(HERE/config["model_bundle"]); now=utcnow()
    local=datetime.now(ZoneInfo("Australia/Brisbane")); day=args.date or local.date().isoformat()
    if not args.force and not args.date and local.weekday()!=5:
        print(json.dumps({"status":"skipped","reason":"not_saturday","local_date":day})); return 0
    live=truthy(os.getenv("TEMPO_COLLECTION_LIVE_ENABLED")) and not args.dry_run
    if not live and not args.dry_run:
        print("Live tempo collection disabled; set TEMPO_COLLECTION_LIVE_ENABLED=true or use --dry-run.",file=sys.stderr); return 2
    url=os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL",""); key=os.getenv("SUPABASE_SERVICE_ROLE_KEY","")
    if live and (not url or not key): print("Supabase URL and service key required",file=sys.stderr); return 2
    db=Supabase(url,key) if live else None; results=[]; errors=[]
    for meeting in discover(day,config):
        try:
            card=fetch_card(meeting["source_meeting_id"])
            results.append(process_meeting(db,meeting,card,bundle,config,now,args.dry_run,
                                           poll_sectionals=args.force or card_is_active(card,now,config)))
        except Exception as exc: errors.append({"meeting":meeting_key(day,meeting["state"],meeting["track_slug"]),"error":str(exc)})
    print(json.dumps({"status":"success" if not errors else "partial","date":day,"meetings":results,"errors":errors},indent=2)); return 1 if errors else 0


if __name__=="__main__": sys.exit(main())
