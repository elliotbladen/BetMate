"""performance-par-v2.0 — adjusted speed figure, the Step-1 rating spine.

Rebuild direction set in `docs/rating_model_selection_2026-09.md` (8 Sep 2026).

`form-first-v2.0` collapsed Step 1 of the ratings architecture into a *collateral*
figure: a winner is rated at the strength of the horses they beat, read off those
horses' official handicap ratings. That misrates a dominant winner behind stale
marks (Lindermann 2026 Chelmsford). The architecture doc is explicit that Step 1
must be *positive performance evidence about the horse itself* — adjusted time,
margin, weight, WFA, pace — and that collateral is a later bounded revision layer
(Step 3), not the base.

This module builds that base as one composed adjusted speed figure. Every
component is stored explicitly and separately in `par_run_performances` so the
figure is fully attributable.

    figure = 100
           + raw_time_vs_par          (par(track,dist,going) - runner_time, in lengths)
           - daily_track_variant       (how fast/slow the whole meeting ran that day)
           + weight_merit              (increment 2 - carried vs reference, race-type aware)
           + pace_adjustment           (increment 3 - slow-run race add-back / collapse dock)
           + class_anchor              (increment 4 - one-sided pull for thin fields only)
           + last400_sectional         (capped)
           + margin_component          (NSW margin-only rows: par vs official winner time, then -beaten)

Coefficients are taken from already-completed research (see the doc), not fitted
here. Validation is the frozen naive chronological protocol in `prediction_test`:
par-v2 must beat BOTH uniform AND performance-par-v1.0 or it is not the spine.

INCREMENT 1 (this commit): scaffold + raw_time_vs_par + daily_track_variant +
last400 sectional + margin. weight_merit / pace_adjustment / class_anchor are
wired as explicit zeros with a `pending` marker.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .performance import (
    NEUTRAL,
    SECONDS_PER_LENGTH,
    build_pars,
    distance_bucket,
    going_bucket,
    utc_now,
)
from .ratings import horse_key
from .step11_models import estimate_daily_variants
from .storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "performance-par-v2.0"
PAR_BASE_MODEL = "performance-par-v1.0"
OUTPUT = ROOT / "reports" / "v2_ratings"

SECTIONAL_CAP_LENGTHS = 2.0        # last-400 evidence stays small until the pace
                                  # layer (increment 3) is in
SECTIONAL_WEIGHT = 0.20
RECENCY_HALF_LIFE_DAYS = 180.0

# Clock sanity. par-v1 has an uncleaned 376-point blowup (audit F10); par-v2 must
# not inherit it. A runner clock more than ~6 s (35 L) off par, or materially
# faster than the official winner's time, is a timing error, not a performance.
MAX_ABS_TIME_LENGTHS = 35.0
FASTER_THAN_WINNER_TOLERANCE_S = 0.20


def clock_is_sane(finish_time: float | None, official_time: float, par_seconds: float) -> bool:
    """A runner clock is usable only if it is not materially faster than the
    official winner and lands within MAX_ABS_TIME_LENGTHS of par."""
    if finish_time is None:
        return False
    if finish_time < official_time - FASTER_THAN_WINNER_TOLERANCE_S:
        return False
    return abs((par_seconds - finish_time) / SECONDS_PER_LENGTH) <= MAX_ABS_TIME_LENGTHS


def compose_figure(raw_time_vs_par: float, daily_variant: float, margin_component: float,
                   weight_merit: float, pace_adjustment: float, class_anchor: float,
                   sectional_component: float) -> float:
    """The par-v2 run figure. Positive daily_variant = the meeting ran fast, so
    it is subtracted. Every other term adds."""
    return (NEUTRAL + raw_time_vs_par - daily_variant + margin_component
            + weight_merit + pace_adjustment + class_anchor + sectional_component)


def schema(store: RacingStore) -> None:
    store.connection.execute("""
    CREATE TABLE IF NOT EXISTS par_run_performances (
      model_version TEXT NOT NULL, as_of_date TEXT NOT NULL,
      source TEXT NOT NULL, race_date TEXT NOT NULL, track_slug TEXT NOT NULL,
      race_number INTEGER NOT NULL, runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL, horse_name TEXT NOT NULL,
      performance_rating REAL NOT NULL,
      raw_time_vs_par REAL NOT NULL,
      daily_variant REAL NOT NULL,
      weight_merit REAL NOT NULL,
      pace_adjustment REAL NOT NULL,
      class_anchor REAL NOT NULL,
      sectional_component REAL NOT NULL,
      margin_component REAL NOT NULL,
      finish_time_used INTEGER NOT NULL,
      par_sample_size INTEGER NOT NULL,
      confidence REAL NOT NULL,
      detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY (model_version, as_of_date, source, race_date, track_slug, race_number, runner_number)
    )""")
    store.connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_par_v2_horse ON par_run_performances(model_version, as_of_date, horse_key)")
    store.connection.commit()


def _last400_components(store: RacingStore, source: str, race_date: str, track_slug: str,
                        race_number: int) -> dict[int, float]:
    """Last-400 split relative to the race median, capped. Same shape as par-v1."""
    rows = store.connection.execute(
        """SELECT runner_number, section_seconds FROM runner_sectionals
             WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ?
               AND marker_metres = 0 AND section_seconds IS NOT NULL""",
        (source, race_date, track_slug, race_number),
    ).fetchall()
    if len(rows) < 3:
        return {}
    median = statistics.median(float(r["section_seconds"]) for r in rows)
    out = {}
    for r in rows:
        lengths = (median - float(r["section_seconds"])) / SECONDS_PER_LENGTH * SECTIONAL_WEIGHT
        out[int(r["runner_number"])] = max(-SECTIONAL_CAP_LENGTHS, min(SECTIONAL_CAP_LENGTHS, lengths))
    return out


def build_performances(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5) -> dict[str, Any]:
    schema(store)
    store.connection.execute("PRAGMA synchronous=OFF")
    store.connection.execute(
        "DELETE FROM par_run_performances WHERE model_version=? AND as_of_date=?", (MODEL_VERSION, as_of_date))

    pars = build_pars(store, as_of_date, min_sample=min_par_sample, model_version=PAR_BASE_MODEL)
    variants = estimate_daily_variants(store, as_of_date, base_model=PAR_BASE_MODEL)

    races = store.connection.execute(
        """SELECT source, race_date, track_slug, race_number, distance_metres,
                  track_condition, official_time_seconds, race_class
             FROM race_results
            WHERE race_date < ? AND distance_metres IS NOT NULL
              AND official_time_seconds IS NOT NULL
            ORDER BY race_date, track_slug, race_number""",
        (as_of_date,),
    ).fetchall()

    now = utc_now()
    counts = defaultdict(int)
    written = 0
    for race in races:
        par_key = (race["track_slug"], distance_bucket(race["distance_metres"]),
                   going_bucket(race["track_condition"]))
        par = pars.get(par_key)
        if par is None:
            counts["no_par"] += 1
            continue
        official_time = float(race["official_time_seconds"])
        if abs((par.time_seconds - official_time) / SECONDS_PER_LENGTH) > MAX_ABS_TIME_LENGTHS:
            counts["race_clock_quarantined"] += 1
            continue
        variant = float(variants.get((race["source"], race["race_date"], race["track_slug"]), 0.0))
        sectional = _last400_components(store, race["source"], race["race_date"],
                                       race["track_slug"], race["race_number"])
        runners = store.connection.execute(
            """SELECT runner_number, runner_name, finish_position, beaten_lengths, finish_time_seconds
                 FROM runner_results
                WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ?
                  AND result_status = 'finished' AND finish_position IS NOT NULL
                ORDER BY runner_number""",
            (race["source"], race["race_date"], race["track_slug"], race["race_number"]),
        ).fetchall()

        for r in runners:
            finish_time = r["finish_time_seconds"]
            ft = float(finish_time) if finish_time is not None else None
            clock_ok = clock_is_sane(ft, official_time, par.time_seconds)
            if finish_time is not None and not clock_ok:
                counts["clock_quarantined"] += 1
            if clock_ok:
                raw_time_vs_par = (par.time_seconds - ft) / SECONDS_PER_LENGTH
                margin_component = 0.0
                finish_time_used = 1
            elif r["beaten_lengths"] is not None:
                raw_time_vs_par = (par.time_seconds - official_time) / SECONDS_PER_LENGTH
                margin_component = -float(r["beaten_lengths"])
                finish_time_used = 0
            else:
                counts["no_clock_no_margin"] += 1
                continue

            sect = sectional.get(int(r["runner_number"]), 0.0)
            weight_merit = 0.0      # increment 2
            pace_adjustment = 0.0   # increment 3
            class_anchor = 0.0      # increment 4

            rating = compose_figure(raw_time_vs_par, variant, margin_component,
                                    weight_merit, pace_adjustment, class_anchor, sect)

            confidence = min(0.80, 0.30 + 0.04 * min(par.sample_size, 8)
                             + (0.10 if finish_time_used else 0.0)
                             + (0.06 if sectional else 0.0)
                             + (0.05 if abs(variant) > 1e-9 else 0.0))

            detail = {
                "par_seconds": par.time_seconds, "par_sample_size": par.sample_size,
                "going_bucket": par.going, "seconds_per_length": SECONDS_PER_LENGTH,
                "daily_variant_version": "daily-track-variant-v1.0",
                "components_pending": ["weight_merit", "pace_adjustment", "class_anchor"],
                "increment": 1,
            }
            store.connection.execute(
                """INSERT INTO par_run_performances VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (MODEL_VERSION, as_of_date, race["source"], race["race_date"], race["track_slug"],
                 race["race_number"], r["runner_number"], horse_key(r["runner_name"]), r["runner_name"],
                 rating, raw_time_vs_par, variant, weight_merit, pace_adjustment, class_anchor,
                 sect, margin_component, finish_time_used, par.sample_size, confidence,
                 json.dumps(detail, sort_keys=True), now))
            written += 1
            counts["performances"] += 1
    store.connection.commit()
    return {"model_version": MODEL_VERSION, "as_of_date": as_of_date,
            "runs_rated": written, "counts": dict(counts),
            "meetings_with_variant": sum(1 for v in variants.values() if abs(v) > 1e-9)}


# ── validation: the frozen naive chronological protocol ──────────────────────

def _softmax(xs: list[float]) -> list[float]:
    m = max(xs); e = [math.exp(x - m) for x in xs]; s = sum(e)
    return [x / s for x in e]


def prediction_test(store: RacingStore, as_of_date: str) -> dict[str, Any]:
    """par-v2 vs par-v1 vs uniform. Median-of-last-3 prior, softmax, temp fit on
    2024, test 2025+. Same protocol as v2_ratings.prediction_test."""
    def history(model_version: str, table: str) -> dict[str, list[tuple[str, float]]]:
        h: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for row in store.connection.execute(
            f"""SELECT race_date, horse_key, performance_rating FROM {table}
                 WHERE model_version=? AND as_of_date=? ORDER BY race_date""",
            (model_version, as_of_date)):
            h[row["horse_key"]].append((row["race_date"], float(row["performance_rating"])))
        return h

    v2 = history(MODEL_VERSION, "par_run_performances")
    v1 = history(PAR_BASE_MODEL, "run_performances")

    races = store.connection.execute(
        """SELECT DISTINCT source, race_date, track_slug, race_number FROM runner_results
            WHERE race_date >= '2024-01-01' AND result_status='finished'
            ORDER BY race_date""").fetchall()

    def prior(hist, key, day):
        vals = [v for d, v in hist.get(key, []) if d < day]
        return statistics.median(vals[-3:]) if vals else 100.0

    examples = []
    for rc in races:
        runners = store.connection.execute(
            """SELECT runner_name, finish_position FROM runner_results
                WHERE source=? AND race_date=? AND track_slug=? AND race_number=?
                  AND result_status='finished' AND finish_position IS NOT NULL
                ORDER BY runner_number""",
            (rc["source"], rc["race_date"], rc["track_slug"], rc["race_number"])).fetchall()
        if len(runners) < 4 or sum(x["finish_position"] == 1 for x in runners) != 1:
            continue
        keys = [horse_key(x["runner_name"]) for x in runners]
        winner = next(i for i, x in enumerate(runners) if x["finish_position"] == 1)
        cov1 = sum(any(d < rc["race_date"] for d, _ in v1.get(k, [])) for k in keys) / len(keys)
        cov2 = sum(any(d < rc["race_date"] for d, _ in v2.get(k, [])) for k in keys) / len(keys)
        if min(cov1, cov2) < 0.60:
            continue
        examples.append({"date": rc["race_date"], "winner": winner, "field": len(keys),
                         "v1": [prior(v1, k, rc["race_date"]) for k in keys],
                         "v2": [prior(v2, k, rc["race_date"]) for k in keys]})

    train = [e for e in examples if e["date"] < "2025-01-01"]
    test = [e for e in examples if e["date"] >= "2025-01-01"]
    temps = (3., 5., 8., 10., 12., 15.)

    def loss(rows, name, t):
        return statistics.mean(-math.log(max(_softmax([v / t for v in e[name]])[e["winner"]], 1e-12)) for e in rows)

    def metrics(name):
        t = min(temps, key=lambda tt: loss(train, name, tt))
        ll, br, hit = [], [], []
        for e in test:
            p = _softmax([v / t for v in e[name]]); w = e["winner"]
            ll.append(-math.log(max(p[w], 1e-12)))
            br.append(sum((pi - (i == w)) ** 2 for i, pi in enumerate(p)))
            hit.append(int(max(range(len(p)), key=p.__getitem__) == w))
        return {"temperature": t, "mean_log_loss": statistics.mean(ll),
                "mean_race_brier": statistics.mean(br), "top_pick_strike_rate": statistics.mean(hit)}

    uniform = {"mean_log_loss": statistics.mean(math.log(e["field"]) for e in test),
               "mean_race_brier": statistics.mean(1 - 1 / e["field"] for e in test)}
    m1, m2 = metrics("v1"), metrics("v2")
    return {"train_races": len(train), "test_races": len(test),
            "par_v1": m1, "par_v2": m2, "uniform": uniform,
            "beats_uniform": m2["mean_log_loss"] < uniform["mean_log_loss"],
            "beats_par_v1": m2["mean_log_loss"] < m1["mean_log_loss"],
            "gate_passed": m2["mean_log_loss"] < uniform["mean_log_loss"] and m2["mean_log_loss"] < m1["mean_log_loss"]}


def leaderboard(store: RacingStore, as_of_date: str, since: str, limit: int = 15) -> list[dict[str, Any]]:
    return [dict(r) for r in store.connection.execute(
        """SELECT p.horse_name, p.performance_rating, p.raw_time_vs_par, p.daily_variant,
                  p.sectional_component, p.race_date, p.track_slug, p.race_number,
                  (SELECT performance_rating FROM run_performances v1
                    WHERE v1.model_version=? AND v1.as_of_date=? AND v1.source=p.source
                      AND v1.race_date=p.race_date AND v1.track_slug=p.track_slug
                      AND v1.race_number=p.race_number AND v1.runner_number=p.runner_number) AS par_v1
             FROM par_run_performances p
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date >= ?
            ORDER BY p.performance_rating DESC LIMIT ?""",
        (PAR_BASE_MODEL, as_of_date, MODEL_VERSION, as_of_date, since, limit))]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    ap.add_argument("--as-of", required=True, help="Exclusive YYYY-MM-DD cutoff")
    ap.add_argument("--min-par-sample", type=int, default=5)
    ap.add_argument("--since", default="2026-08-01")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--test", action="store_true", help="run the naive predictive gate")
    args = ap.parse_args()
    store = RacingStore(args.database)
    try:
        report = build_performances(store, args.as_of, min_par_sample=args.min_par_sample)
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.test:
            print("\n=== naive predictive gate (par-v2 vs par-v1 vs uniform) ===")
            print(json.dumps(prediction_test(store, args.as_of), indent=2, sort_keys=True))
        print(f"\nTOP {args.top} par-v2 runs since {args.since}")
        print(f"  {'horse':<20}{'v2':>7}{'v1':>7}{'tvp':>7}{'var':>7}  {'race':<26}")
        for x in leaderboard(store, args.as_of, args.since, args.top):
            v1 = f"{x['par_v1']:.1f}" if x['par_v1'] is not None else "  -"
            print(f"  {x['horse_name']:<20}{x['performance_rating']:>7.1f}{v1:>7}"
                  f"{x['raw_time_vs_par']:>7.1f}{x['daily_variant']:>7.2f}  "
                  f"{x['track_slug'][:12]+' R'+str(x['race_number']):<26}")
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "par_v2_build_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
