"""Research hierarchical class priors from pre-race official rating evidence."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from .storage import RacingStore, utc_now


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_VERSION = "class-prior-research-v1.0"
MIN_RATED_RUNNERS = 3


def _subtype(row: dict[str, Any]) -> str:
    if row["group_grade"] is not None:
        return f"group:{int(row['group_grade'])}"
    if row["benchmark"] is not None:
        return f"benchmark:{int(row['benchmark'])}"
    if row["class_number"] is not None:
        return f"class:{int(row['class_number'])}"
    return "unspecified"


def _variance(values: list[float]) -> float:
    return statistics.pvariance(values) if len(values) > 1 else 0.0


def _prior_strength(groups: dict[str, list[dict[str, Any]]], raw_means: dict[str, float]) -> float:
    """Empirical-Bayes equivalent race count, bounded for sparse hierarchies."""
    within_parts = []
    for key, races in groups.items():
        values = [race["field_median_rating"] for race in races]
        if len(values) > 1:
            within_parts.append(_variance(values))
    within = statistics.mean(within_parts) if within_parts else 25.0
    between = _variance(list(raw_means.values()))
    if between <= 1e-9:
        return 100.0
    return max(5.0, min(100.0, within / between))


def research(store: RacingStore, as_of_date: str, *, research_version: str = RESEARCH_VERSION) -> dict[str, Any]:
    # This table is a reproducible derived artefact. Remove stale groups from a
    # prior build of the same version/cutoff before recreating the full set.
    store.connection.execute(
        "DELETE FROM class_prior_research WHERE research_version=? AND as_of_date=?",
        (research_version, as_of_date),
    )
    race_rows = store.connection.execute(
        """SELECT rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.state,
                  rc.class_family,rc.group_grade,rc.benchmark,rc.class_number,rc.raw_class_text
             FROM race_results rr JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
            WHERE rr.race_date < ? ORDER BY rr.race_date,rr.track_slug,rr.race_number""", (as_of_date,)).fetchall()
    races: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    all_finished = all_rated = 0
    for row in race_rows:
        runners = store.connection.execute(
            """SELECT official_handicap_rating FROM runner_results
               WHERE source=? AND race_date=? AND track_slug=? AND race_number=? AND result_status='finished'""",
            (row["source"], row["race_date"], row["track_slug"], row["race_number"])).fetchall()
        ratings = [float(r[0]) for r in runners if r[0] is not None and float(r[0]) > 0]
        all_finished += len(runners); all_rated += len(ratings)
        if len(ratings) < MIN_RATED_RUNNERS:
            exclusions["fewer_than_three_rated_runners"] += 1
            continue
        ordered = sorted(ratings, reverse=True)
        item = dict(row)
        item.update({"field_median_rating": statistics.median(ratings),
                     "field_top4_rating": statistics.mean(ordered[:4]),
                     "rated_runners": len(ratings), "finished_runners": len(runners),
                     "subtype": _subtype(dict(row))})
        races.append(item)

    levels: list[tuple[str, Callable[[dict[str, Any]], str], Callable[[dict[str, Any]], str | None]]] = [
        ("global", lambda r: "all", lambda r: None),
        ("state", lambda r: r["state"], lambda r: "all"),
        ("class_family", lambda r: f"{r['state']}|{r['class_family']}", lambda r: r["state"]),
        ("venue_class", lambda r: f"{r['state']}|{r['class_family']}|{r['track_slug']}",
         lambda r: f"{r['state']}|{r['class_family']}"),
        ("subtype", lambda r: f"{r['state']}|{r['class_family']}|{r['track_slug']}|{r['subtype']}",
         lambda r: f"{r['state']}|{r['class_family']}|{r['track_slug']}"),
    ]
    prior_values: dict[tuple[str, str], float] = {}
    output: dict[str, list[dict[str, Any]]] = {}
    now = utc_now()
    previous_level: str | None = None
    for level, key_fn, parent_fn in levels:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for race in races:
            groups[key_fn(race)].append(race)
        raw_means = {key: statistics.mean(r["field_median_rating"] for r in values)
                     for key, values in groups.items()}
        strength = 0.0 if level == "global" else _prior_strength(groups, raw_means)
        rows_out = []
        for key, values in sorted(groups.items()):
            parent_key = parent_fn(values[0])
            raw = raw_means[key]
            if parent_key is None:
                weight, shrunk = 1.0, raw
            else:
                parent = prior_values[(previous_level, parent_key)]
                weight = len(values) / (len(values) + strength)
                shrunk = weight * raw + (1 - weight) * parent
            uncertainty = statistics.pstdev([r["field_median_rating"] for r in values]) / math.sqrt(len(values)) if len(values) > 1 else None
            coverage = sum(r["rated_runners"] for r in values) / sum(r["finished_runners"] for r in values)
            top4 = statistics.mean(r["field_top4_rating"] for r in values)
            result = {"group_key": key, "parent_key": parent_key, "races": len(values),
                      "runner_rating_coverage": coverage, "raw_mean_field_rating": raw,
                      "raw_mean_top4_rating": top4, "shrunk_field_rating": shrunk,
                      "shrinkage_weight": weight, "prior_strength_races": strength,
                      "uncertainty": uncertainty}
            rows_out.append(result); prior_values[(level, key)] = shrunk
            store.connection.execute(
                """INSERT INTO class_prior_research
                   (research_version,as_of_date,level,group_key,parent_key,races,runner_rating_coverage,
                    raw_mean_field_rating,shrunk_field_rating,shrinkage_weight,prior_strength_races,
                    uncertainty,detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(research_version,as_of_date,level,group_key) DO UPDATE SET
                    parent_key=excluded.parent_key,races=excluded.races,
                    runner_rating_coverage=excluded.runner_rating_coverage,
                    raw_mean_field_rating=excluded.raw_mean_field_rating,
                    shrunk_field_rating=excluded.shrunk_field_rating,
                    shrinkage_weight=excluded.shrinkage_weight,prior_strength_races=excluded.prior_strength_races,
                    uncertainty=excluded.uncertainty,detail_json=excluded.detail_json,created_at=excluded.created_at""",
                (research_version, as_of_date, level, key, parent_key, len(values), coverage, raw, shrunk,
                 weight, strength, uncertainty, json.dumps({"raw_mean_top4_rating": top4,
                 "evidence": "pre-race official handicap ratings", "minimum_rated_runners": MIN_RATED_RUNNERS}, sort_keys=True), now))
        output[level] = rows_out
        previous_level = level
    store.connection.commit()
    unclassified = sum(r["class_family"] == "unclassified" for r in races)
    sparse_subtypes = sum(row["races"] < 5 for row in output["subtype"])
    bound_levels = {
        level: sorted({row["prior_strength_races"] for row in level_rows})
        for level, level_rows in output.items()
        if level != "global" and any(row["prior_strength_races"] in (5.0, 100.0) for row in level_rows)
    }
    return {"research_version": research_version, "as_of_date": as_of_date,
            "evidence": "race median and top-four pre-race official handicap rating",
            "race_results": len(race_rows), "eligible_races": len(races),
            "excluded_races": sum(exclusions.values()), "exclusion_reasons": dict(exclusions),
            "runner_rating_coverage": all_rated / all_finished if all_finished else None,
            "unclassified_eligible_races": unclassified, "levels": output,
            "diagnostics": {"sparse_subtype_groups_under_five_races": sparse_subtypes,
                            "subtype_groups": len(output["subtype"]),
                            "prior_strength_bound_levels": bound_levels,
                            "restricted_scope": "NSW and VIC Saturday metropolitan meetings only"},
            "model_integration": "none; descriptive research only"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--as-of", required=True, help="Exclusive YYYY-MM-DD cutoff")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        report = research(store, args.as_of)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
