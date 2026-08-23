"""Build pre-race Race Strength while isolating completed-race evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .class_prior_research import RESEARCH_VERSION, research
from .field_strength import FIELD_MODEL_VERSION
from .storage import RacingStore, utc_now


ROOT = Path(__file__).resolve().parents[1]
RACE_STRENGTH_VERSION = "race-strength-v1.0"
EVIDENCE_VERSION = "post-race-strength-evidence-v1.0"
NEUTRAL = 100.0


def subtype(row: Any) -> str:
    if row["group_grade"] is not None:
        return f"group:{int(row['group_grade'])}"
    if row["benchmark"] is not None:
        return f"benchmark:{int(row['benchmark'])}"
    if row["class_number"] is not None:
        return f"class:{int(row['class_number'])}"
    return "unspecified"


def class_keys(row: Any) -> list[tuple[str, str]]:
    state, family, track = row["state"], row["class_family"], row["track_slug"]
    return [("subtype", f"{state}|{family}|{track}|{subtype(row)}"),
            ("venue_class", f"{state}|{family}|{track}"),
            ("class_family", f"{state}|{family}"), ("state", state), ("global", "all")]


def combine_components(*, class_prior: float | None, global_prior: float | None,
                       class_reliability: float, field_median: float, field_top4: float,
                       rated_coverage: float, field_uncertainty: float) -> dict[str, float | None]:
    """Map class evidence onto the internal neutral-100 scale and blend by reliability."""
    class_only = (NEUTRAL + class_prior - global_prior
                  if class_prior is not None and global_prior is not None else None)
    field_only = 0.60 * field_median + 0.40 * field_top4
    # Coverage is the main reliability gate. High uncertainty reduces the
    # field's say further, but never changes the underlying field-only value.
    field_reliability = rated_coverage * max(0.0, min(1.0, 1.0 - field_uncertainty / 20.0))
    usable_class_reliability = class_reliability if class_only is not None else 0.0
    total = usable_class_reliability + field_reliability
    if total:
        combined = ((class_only or 0.0) * usable_class_reliability + field_only * field_reliability) / total
    else:
        combined = NEUTRAL
    return {"class_only_rating": class_only, "field_only_rating": field_only,
            "class_reliability": usable_class_reliability, "field_reliability": field_reliability,
            "combined_rating": combined}


def _prior_lookup(store: RacingStore, as_of_date: str) -> dict[tuple[str, str], Any]:
    return {(row["level"], row["group_key"]): row for row in store.connection.execute(
        """SELECT * FROM class_prior_research
           WHERE research_version=? AND as_of_date=?""", (RESEARCH_VERSION, as_of_date))}


def build_race_strength(store: RacingStore, *, from_date: str | None = None, to_date: str | None = None,
                        version: str = RACE_STRENGTH_VERSION) -> dict[str, Any]:
    clauses, parameters = [], []
    if from_date:
        clauses.append("rr.race_date>=?"); parameters.append(from_date)
    if to_date:
        clauses.append("rr.race_date<=?"); parameters.append(to_date)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    dates = [row[0] for row in store.connection.execute(
        "SELECT DISTINCT rr.race_date FROM race_results rr" + where + " ORDER BY rr.race_date", parameters)]
    now = utc_now(); stored = 0; fallback_levels: Counter[str] = Counter()
    for race_date in dates:
        research(store, race_date)
        priors = _prior_lookup(store, race_date)
        global_row = priors.get(("global", "all"))
        races = store.connection.execute(
            """SELECT rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.state,
                      rc.class_family,rc.group_grade,rc.benchmark,rc.class_number,
                      f.field_median_rating,f.top_four_mean_rating,f.depth_within_five,
                      f.rated_coverage,f.field_uncertainty,f.rated_runners,f.starters
                 FROM race_results rr JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
                 JOIN pre_race_field_strengths f USING(source,race_date,track_slug,race_number)
                WHERE rr.race_date=? AND f.field_model_version=?
                ORDER BY rr.track_slug,rr.race_number,rr.source""", (race_date, FIELD_MODEL_VERSION)).fetchall()
        for race in races:
            chosen_level = chosen_key = None; prior = None
            for level, key in class_keys(race):
                if (level, key) in priors:
                    chosen_level, chosen_key, prior = level, key, priors[(level, key)]; break
            fallback_levels[chosen_level or "no_prior"] += 1
            reliability = float(prior["shrinkage_weight"]) if prior else 0.0
            components = combine_components(
                class_prior=float(prior["shrunk_field_rating"]) if prior else None,
                global_prior=float(global_row["shrunk_field_rating"]) if global_row else None,
                class_reliability=reliability, field_median=float(race["field_median_rating"]),
                field_top4=float(race["top_four_mean_rating"]), rated_coverage=float(race["rated_coverage"]),
                field_uncertainty=float(race["field_uncertainty"]))
            identity = (race["source"], race_date, race["track_slug"], race["race_number"])
            detail = {"formula": "reliability_weighted_class_and_field_v1",
                      "class_mapping": "100 + shrunk class prior - as-of global prior",
                      "field_formula": "0.60 * median + 0.40 * top_four",
                      "field_reliability_formula": "coverage * (1 - uncertainty / 20)",
                      "class_sample_races": int(prior["races"]) if prior else 0,
                      "class_uncertainty": prior["uncertainty"] if prior else None,
                      "field_depth": int(race["depth_within_five"]),
                      "rated_runners": int(race["rated_runners"]), "starters": int(race["starters"])}
            store.connection.execute(
                """INSERT INTO race_strength_ratings
                   (race_strength_version,source,race_date,track_slug,race_number,class_prior_level,class_prior_key,
                    class_prior_official_scale,class_global_official_scale,class_only_rating,class_reliability,
                    field_only_rating,field_reliability,combined_rating,rated_coverage,field_uncertainty,
                    information_cutoff,component_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(race_strength_version,source,race_date,track_slug,race_number) DO UPDATE SET
                    class_prior_level=excluded.class_prior_level,class_prior_key=excluded.class_prior_key,
                    class_prior_official_scale=excluded.class_prior_official_scale,
                    class_global_official_scale=excluded.class_global_official_scale,class_only_rating=excluded.class_only_rating,
                    class_reliability=excluded.class_reliability,field_only_rating=excluded.field_only_rating,
                    field_reliability=excluded.field_reliability,combined_rating=excluded.combined_rating,
                    rated_coverage=excluded.rated_coverage,field_uncertainty=excluded.field_uncertainty,
                    information_cutoff=excluded.information_cutoff,component_json=excluded.component_json,
                    created_at=excluded.created_at""",
                (version, *identity, chosen_level, chosen_key,
                 float(prior["shrunk_field_rating"]) if prior else None,
                 float(global_row["shrunk_field_rating"]) if global_row else None,
                 components["class_only_rating"], components["class_reliability"], components["field_only_rating"],
                 components["field_reliability"], components["combined_rating"], race["rated_coverage"],
                 race["field_uncertainty"], race_date, json.dumps(detail, sort_keys=True), now))
            result_runners = store.connection.execute(
                """SELECT finish_position,beaten_lengths,finish_time_seconds,result_status FROM runner_results
                   WHERE source=? AND race_date=? AND track_slug=? AND race_number=?""", identity).fetchall()
            finishers = [row for row in result_runners if row["result_status"] == "finished"]
            winner_time = next((row["finish_time_seconds"] for row in finishers if row["finish_position"] == 1), None)
            official_time = store.connection.execute(
                "SELECT official_time_seconds FROM race_results WHERE source=? AND race_date=? AND track_slug=? AND race_number=?",
                identity).fetchone()[0]
            evidence = {"separate_from_pre_race_rating": True,
                        "margin_observations": sum(row["beaten_lengths"] is not None for row in finishers),
                        "runner_time_observations": sum(row["finish_time_seconds"] is not None for row in finishers)}
            store.connection.execute(
                """INSERT INTO post_race_strength_evidence
                   (evidence_version,source,race_date,track_slug,race_number,official_time_seconds,winner_time_seconds,
                    finishers,margin_observations,runner_time_observations,evidence_json,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(evidence_version,source,race_date,track_slug,race_number)
                   DO UPDATE SET official_time_seconds=excluded.official_time_seconds,winner_time_seconds=excluded.winner_time_seconds,
                    finishers=excluded.finishers,margin_observations=excluded.margin_observations,
                    runner_time_observations=excluded.runner_time_observations,evidence_json=excluded.evidence_json,
                    created_at=excluded.created_at""",
                (EVIDENCE_VERSION, *identity, official_time, winner_time, len(finishers),
                 evidence["margin_observations"], evidence["runner_time_observations"], json.dumps(evidence, sort_keys=True), now))
            stored += 1
        store.connection.commit()
    return {"race_strength_version": version, "from_date": from_date, "to_date": to_date,
            "dates": len(dates), "races": stored, "class_prior_fallback_levels": dict(sorted(fallback_levels.items())),
            "post_race_evidence_separate": True, "model_integration": "none until Step 9"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--from-date"); parser.add_argument("--to-date"); parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try:
        report = build_race_strength(store, from_date=args.from_date, to_date=args.to_date)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
