"""Durable horse profiles and point-in-time Australian racing ages."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from .storage import RacingStore, utc_now


DERIVATION_VERSION = "horse-profile-age-v1.0"
FEMALE_SEXES = {"F", "FILLY", "M", "MARE"}
SEX_CODES = {"COLT": "C", "GELDING": "G", "HORSE": "H", "RIG": "R",
             "FILLY": "F", "MARE": "M"}


def normalise_sex(value: object) -> str | None:
    text = str(value or "").strip().upper()
    return SEX_CODES.get(text, text if text in set(SEX_CODES.values()) else None)


def normalise_country(value: object) -> str | None:
    match = re.search(r"[A-Z]{2,3}", str(value or "").upper())
    return match.group(0) if match else None


def australian_racing_age(birth_date: str | date, race_date: str | date, *,
                          dam_first_covered_before_previous_september: bool = False) -> int:
    """Apply AR 161's 1-August age reckoning to a known foaling date.

    The exceptional July-December early-cover case needs Stud Book provenance;
    callers must opt into it rather than having it guessed.
    """
    born = date.fromisoformat(birth_date) if isinstance(birth_date, str) else birth_date
    raced = date.fromisoformat(race_date) if isinstance(race_date, str) else race_date
    if raced < born:
        raise ValueError("race date precedes birth date")
    season_year = raced.year if raced.month >= 8 else raced.year - 1
    reference_year = born.year - 1 if born.month <= 6 or dam_first_covered_before_previous_september else born.year
    return max(0, season_year - reference_year)


def age_from_observation(observed_age: int, observed_date: str | date,
                         race_date: str | date) -> int:
    """Move a reported racing age across Australian 1-Aug season boundaries."""
    observed = date.fromisoformat(observed_date) if isinstance(observed_date, str) else observed_date
    raced = date.fromisoformat(race_date) if isinstance(race_date, str) else race_date
    observed_season = observed.year if observed.month >= 8 else observed.year - 1
    race_season = raced.year if raced.month >= 8 else raced.year - 1
    age = int(observed_age) + race_season - observed_season
    if age < 0:
        raise ValueError("derived racing age is negative")
    return age


def record_observation(store: RacingStore, *, horse_id: str, profile_source: str,
                       source_horse_id: str, observed_at: str, birth_date: str | None,
                       observed_racing_age: int | None, sex: str | None,
                       country_code: str | None, source_url: str | None,
                       confidence: float = 1.0, detail: dict[str, Any] | None = None) -> None:
    now = utc_now()
    store.connection.execute(
        """INSERT INTO horse_profile_observations
           (profile_source,source_horse_id,horse_id,observed_at,birth_date,observed_racing_age,
            sex,country_code,source_url,confidence,detail_json,imported_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(profile_source,source_horse_id,observed_at)
           DO UPDATE SET horse_id=excluded.horse_id,birth_date=excluded.birth_date,
             observed_racing_age=excluded.observed_racing_age,sex=excluded.sex,
             country_code=excluded.country_code,source_url=excluded.source_url,
             confidence=excluded.confidence,detail_json=excluded.detail_json""",
        (profile_source, str(source_horse_id), horse_id, observed_at, birth_date,
         observed_racing_age, normalise_sex(sex), normalise_country(country_code), source_url,
         confidence, json.dumps(detail or {}, sort_keys=True), now))
    store.connection.commit()


def ingest_racing_com_observations(store: RacingStore) -> dict[str, int]:
    """Extract profile facts already archived inside Racing.com result rows."""
    rows = store.connection.execute(
        """SELECT rr.*,l.horse_id FROM runner_results rr JOIN runner_horse_links l
             USING(source,race_date,track_slug,race_number,runner_number)
            WHERE rr.source LIKE 'racing-com%' ORDER BY rr.race_date""").fetchall()
    seen = usable = 0
    for row in rows:
        seen += 1
        raw = json.loads(row["raw_json"])
        entry = raw.get("raw_entry", raw)
        horse = entry.get("horse") or {}
        if not horse.get("id"):
            continue
        age_match = re.search(r"\d+", str(horse.get("age") or ""))
        age = int(age_match.group()) if age_match else None
        record_observation(
            store, horse_id=row["horse_id"], profile_source="racing-com-rv-authorised",
            source_horse_id=str(horse["id"]), observed_at=row["race_date"], birth_date=None,
            observed_racing_age=age,
            sex=horse.get("sex"), country_code=horse.get("country"),
            source_url=f"https://www.racing.com/form/{row['race_date']}/{row['track_slug']}",
            detail={"colour": horse.get("colour"), "full_name": horse.get("fullName"),
                    "birth_date_status": "not_exposed_by_source"})
        usable += 1
    return {"runner_rows_checked": seen, "profile_observations_written": usable}


def derive_runner_profiles(store: RacingStore) -> dict[str, int]:
    """Materialise age/sex/country for each linked historical appearance."""
    runners = store.connection.execute(
        """SELECT rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.runner_number,l.horse_id
             FROM runner_results rr JOIN runner_horse_links l
             USING(source,race_date,track_slug,race_number,runner_number)""").fetchall()
    derived = missing = 0
    now = utc_now()
    for runner in runners:
        observations = store.connection.execute(
            """SELECT * FROM horse_profile_observations WHERE horse_id=?
                 ORDER BY (birth_date IS NOT NULL) DESC,
                          ABS(julianday(observed_at)-julianday(?)), observed_at""",
            (runner["horse_id"], runner["race_date"])).fetchall()
        if not observations:
            missing += 1
            continue
        profile = observations[0]
        if profile["birth_date"]:
            age = australian_racing_age(profile["birth_date"], runner["race_date"])
            method = "ar161_exact_birth_date"
        elif profile["observed_racing_age"] is not None:
            age = age_from_observation(profile["observed_racing_age"], profile["observed_at"], runner["race_date"])
            method = "ar161_season_projection_from_official_observed_age"
        else:
            age = None
            method = None
        profile_detail = json.loads(profile["detail_json"] or "{}")
        sire_country = profile_detail.get("sire_country_code")
        birth_month = int(profile["birth_date"][5:7]) if profile["birth_date"] else None
        ar170_eligible = bool(sire_country in {"GB", "IRE", "FR", "GER", "USA", "CAN", "JPN"}
                              and birth_month is not None and birth_month <= 7)
        store.connection.execute(
            """INSERT INTO runner_derived_profiles
               (derivation_version,source,race_date,track_slug,race_number,runner_number,horse_id,
                birth_date,racing_age,age_method,sex,country_code,profile_source,source_observed_at,
                detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(derivation_version,source,race_date,track_slug,race_number,runner_number)
               DO UPDATE SET horse_id=excluded.horse_id,birth_date=excluded.birth_date,
                 racing_age=excluded.racing_age,age_method=excluded.age_method,sex=excluded.sex,
                 country_code=excluded.country_code,profile_source=excluded.profile_source,
                 source_observed_at=excluded.source_observed_at,detail_json=excluded.detail_json,
                 created_at=excluded.created_at""",
            (DERIVATION_VERSION, runner["source"], runner["race_date"], runner["track_slug"],
             runner["race_number"], runner["runner_number"], runner["horse_id"], profile["birth_date"],
             age, method, profile["sex"], profile["country_code"], profile["profile_source"],
             profile["observed_at"], json.dumps({"profile_confidence": profile["confidence"],
                "sire_country_code": sire_country, "ar170_eligible": ar170_eligible,
                "ar170_status": "eligible" if ar170_eligible else
                    ("not_eligible" if sire_country and birth_month else "missing_sire_or_foal_month")},
                sort_keys=True), now))
        derived += 1
    store.connection.commit()
    return {"runner_rows": len(runners), "derived_profiles": derived, "missing_profiles": missing}
