"""form-first-v3.1 — par-v2 speed figure + bounded franked collateral, then a
consolidated per-horse current-ability rating.

The rating architecture wants Step 1 to be the horse's own adjusted performance
(that is `performance-par-v2.0`) and Step 3 to be a *collateral network* that
revises an earlier race as its participants run again — NOT a collateral figure
that sets the base (form-first-v2.0's mistake, which rated Lindermann's Chelmsford
off Ceolwulf's stale official 119).

INCREMENT 7 — franked runs (`form-first-v3.1`)
  base            = par-v2 run figure
  franking        = for each race, once its beaten top-4 have run again, re-anchor
                    the race level on the beaten field's *later demonstrated*
                    par-v2 ability + adjusted beaten margin. Bounded, partial
                    credit, strictly as-of (only later runs before the cutoff).
  v3.1_figure     = par_v2_figure + clip(franking_revision, +/- FRANK_BOUND)

INCREMENT 8 — per-horse current rating (`par_v2_horse_rating_states`)
  recency-weighted blend of the horse's v3.1 run figures, reliability shrinkage,
  explicit uncertainty; THEN a recent head-to-head cap — a horse cannot out-rate
  a horse that finished in front of it at its most recent start (the winner
  franks the form), give or take weight-for-weight relief.
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

from .performance import utc_now
from .storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
PAR_V2_MODEL = "performance-par-v2.0"
RUN_MODEL_VERSION = "form-first-v3.1"
STATE_MODEL_VERSION = "par-v2-ability-v1.0"
OUTPUT = ROOT / "reports" / "v2_ratings"
NEUTRAL = 100.0

# ── franking ────────────────────────────────────────────────────────────────
FRANK_WEIGHT = 0.55          # partial credit; the beaten field's later form is noisy
FRANK_BOUND = 6.0            # max lengths the franking can move a race level
FRANK_MIN_LATER_RUNS = 1     # later runs a beaten horse needs to contribute
FRANK_MIN_CONTRIBUTORS = 2   # beaten horses with later form needed to frank at all
FRANK_LATER_RUN_WINDOW = 3   # use the beaten horse's first few later runs
MARGIN_KNEE, MARGIN_TAPER = 4.0, 0.45

# ── per-horse current rating ────────────────────────────────────────────────
# 90-day half-life: a thoroughbred's form from a campaign or more ago is only
# lightly relevant to what it is now. (par-v1's states use 180 — too long here.)
RECENCY_HALF_LIFE_DAYS = 90.0

# ── head-to-head cap ────────────────────────────────────────────────────────
H2H_CAP_MAX_AGE_DAYS = 75    # a head-to-head older than this is stale, ignore it
H2H_CAP_EPSILON = 0.1        # the beaten horse sits at least this far behind
WEIGHT_MERIT_PTS_PER_KG_HCP = 0.9
WEIGHT_MERIT_PTS_PER_KG_WFA = 0.2


def _adj_margin(m: float) -> float:
    return m if m <= MARGIN_KNEE else MARGIN_KNEE + (m - MARGIN_KNEE) * MARGIN_TAPER


def franking_revision(winner_figure: float, anchors: list[float], contributors: int) -> float:
    """Bounded partial-credit revision to a race level from the beaten field's
    later demonstrated ability. Zero until at least FRANK_MIN_CONTRIBUTORS beaten
    horses have run again."""
    if contributors < FRANK_MIN_CONTRIBUTORS or not anchors:
        return 0.0
    collateral = statistics.median(anchors)
    return max(-FRANK_BOUND, min(FRANK_BOUND, (collateral - winner_figure) * FRANK_WEIGHT))


def schema(store: RacingStore) -> None:
    store.connection.execute("""
    CREATE TABLE IF NOT EXISTS franked_run_performances (
      model_version TEXT NOT NULL, as_of_date TEXT NOT NULL,
      race_date TEXT NOT NULL, track_slug TEXT NOT NULL, race_number INTEGER NOT NULL,
      runner_number INTEGER NOT NULL, horse_key TEXT NOT NULL, horse_name TEXT NOT NULL,
      finish_position INTEGER NOT NULL, beaten_lengths REAL,
      par_v2_figure REAL NOT NULL, franking_revision REAL NOT NULL,
      performance_rating REAL NOT NULL, frank_contributors INTEGER NOT NULL,
      frank_effective_from TEXT,
      confidence REAL NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY (model_version, as_of_date, race_date, track_slug, race_number, runner_number)
    )""")
    store.connection.execute("""
    CREATE TABLE IF NOT EXISTS par_v2_horse_rating_states (
      model_version TEXT NOT NULL, as_of_date TEXT NOT NULL,
      horse_key TEXT NOT NULL, horse_name TEXT NOT NULL,
      overall_rating REAL NOT NULL, peak_rating REAL NOT NULL,
      recent_rating REAL NOT NULL, rated_runs INTEGER NOT NULL,
      reliability REAL NOT NULL, uncertainty REAL NOT NULL,
      last_run_date TEXT NOT NULL, h2h_capped_to REAL,
      detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY (model_version, as_of_date, horse_key)
    )""")
    store.connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_franked_horse ON franked_run_performances(model_version, as_of_date, horse_key)")
    store.connection.commit()


# ── load a clean one-row-per-runner view of par-v2 ──────────────────────────

def _load_par_v2(store: RacingStore, as_of_date: str):
    """(race_date, track, num) -> list of runner dicts, best source per runner."""
    best: dict[tuple, dict] = {}
    for r in store.connection.execute(
        """SELECT p.race_date, p.track_slug, p.race_number, p.runner_number, p.horse_key,
                  p.horse_name, p.performance_rating, p.confidence,
                  rr.finish_position, rr.beaten_lengths, rr.weight_carried_kg, race.race_class
             FROM par_run_performances p
             JOIN runner_results rr USING (source, race_date, track_slug, race_number, runner_number)
             JOIN race_results race USING (source, race_date, track_slug, race_number)
            WHERE p.model_version = ? AND p.as_of_date = ?""",
        (PAR_V2_MODEL, as_of_date)):
        key = (r["race_date"], r["track_slug"], r["race_number"], r["runner_number"])
        if key not in best or r["confidence"] > best[key]["confidence"]:
            best[key] = dict(r)
    races: dict[tuple, list] = defaultdict(list)
    for (d, t, n, _rn), row in best.items():
        races[(d, t, n)].append(row)
    for rows in races.values():
        rows.sort(key=lambda x: (x["finish_position"] is None, x["finish_position"] or 999))
    return races


def _weight_factor(race_class: str | None) -> float:
    t = (race_class or "").lower()
    wfa = ("weight for age", "weight-for-age", "wfa", "set weight", "standard weight")
    return WEIGHT_MERIT_PTS_PER_KG_WFA if any(m in t for m in wfa) else WEIGHT_MERIT_PTS_PER_KG_HCP


# ── increment 7: franked runs ──────────────────────────────────────────────

def build_franked_runs(store: RacingStore, as_of_date: str) -> dict[str, Any]:
    schema(store)
    store.connection.execute(
        "DELETE FROM franked_run_performances WHERE model_version=? AND as_of_date=?",
        (RUN_MODEL_VERSION, as_of_date))
    races = _load_par_v2(store, as_of_date)

    # per-horse chronological par-v2 history (for "later form")
    hist: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (d, _t, _n), rows in races.items():
        for row in rows:
            hist[row["horse_key"]].append((d, row["performance_rating"]))
    for v in hist.values():
        v.sort()

    def later_form(horse_key: str, after: str) -> tuple[float, str] | None:
        """Median of the beaten horse's next few runs, plus the date that
        evidence became available. The date is what makes the revision
        effective-dated: before it, the franking simply did not exist."""
        laters = [(d, fig) for d, fig in hist.get(horse_key, []) if after < d < as_of_date]
        if len(laters) < FRANK_MIN_LATER_RUNS:
            return None
        window = laters[:FRANK_LATER_RUN_WINDOW]
        return statistics.median(f for _d, f in window), window[-1][0]

    now = utc_now()
    counts = defaultdict(int)
    written = 0
    for (race_date, track_slug, race_number), rows in sorted(races.items()):
        winner = next((r for r in rows if r["finish_position"] == 1), None)
        if winner is None:
            counts["no_winner"] += 1
            continue
        winner_fig = winner["performance_rating"]

        anchors, contributors, contributor_dates = [], 0, []
        for r in rows:
            if r["finish_position"] in (None, 1) or r["finish_position"] > 5:
                continue
            got = later_form(r["horse_key"], race_date)
            if got is None:
                continue
            lf, evidence_date = got
            margin = abs(r["beaten_lengths"]) if r["beaten_lengths"] is not None else 0.5
            anchors.append(lf + _adj_margin(margin))
            contributor_dates.append(evidence_date)
            contributors += 1

        revision = franking_revision(winner_fig, anchors, contributors)
        # The revision only exists once FRANK_MIN_CONTRIBUTORS beaten horses have
        # run again, so it becomes knowable on the date the Nth of them ran.
        effective_from = None
        if revision:
            counts["franked"] += 1
            effective_from = sorted(contributor_dates)[FRANK_MIN_CONTRIBUTORS - 1]

        for r in rows:
            fig = r["performance_rating"] + revision
            detail = {"par_v2_figure": r["performance_rating"], "franking_revision": revision,
                      "frank_contributors": contributors,
                      "frank_effective_from": effective_from,
                      "frank_status": "franked" if revision else "not yet franked (beaten field has not run again)"}
            store.connection.execute(
                """INSERT INTO franked_run_performances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (RUN_MODEL_VERSION, as_of_date, race_date, track_slug, race_number, r["runner_number"],
                 r["horse_key"], r["horse_name"], r["finish_position"], r["beaten_lengths"],
                 r["performance_rating"], revision, fig, contributors, effective_from, r["confidence"],
                 json.dumps(detail, sort_keys=True), now))
            written += 1
    store.connection.commit()
    return {"model_version": RUN_MODEL_VERSION, "as_of_date": as_of_date,
            "runs_rated": written, "counts": dict(counts)}


# ── increment 8: per-horse current rating + head-to-head cap ────────────────

def build_horse_ratings(store: RacingStore, as_of_date: str) -> dict[str, Any]:
    schema(store)
    store.connection.execute(
        "DELETE FROM par_v2_horse_rating_states WHERE model_version=? AND as_of_date=?",
        (STATE_MODEL_VERSION, as_of_date))

    runs = store.connection.execute(
        """SELECT race_date, track_slug, race_number, runner_number, horse_key, horse_name,
                  finish_position, beaten_lengths, performance_rating, confidence
             FROM franked_run_performances WHERE model_version=? AND as_of_date=?
            ORDER BY horse_key, race_date""",
        (RUN_MODEL_VERSION, as_of_date)).fetchall()

    by_horse: dict[str, list] = defaultdict(list)
    for r in runs:
        by_horse[r["horse_key"]].append(r)
    cutoff = date.fromisoformat(as_of_date)

    states: dict[str, dict] = {}
    for key, rs in by_horse.items():
        weights, values = [], []
        for run in rs:
            age = max(0, (cutoff - date.fromisoformat(run["race_date"])).days)
            w = math.exp(-math.log(2) * age / RECENCY_HALF_LIFE_DAYS) * float(run["confidence"])
            weights.append(w); values.append(float(run["performance_rating"]))
        wmean = sum(w * v for w, v in zip(weights, values)) / sum(weights)
        reliability = 1.0 - math.exp(-len(rs) / 4.0)
        overall = NEUTRAL + reliability * (wmean - NEUTRAL)
        consistency = statistics.pstdev(values) if len(values) > 1 else 0.0
        states[key] = {
            "horse_key": key, "horse_name": rs[-1]["horse_name"],
            "overall_rating": overall, "peak_rating": max(values),
            "recent_rating": values[-1], "rated_runs": len(rs), "reliability": reliability,
            "uncertainty": max(2.0, 12.0 * (1.0 - reliability) + consistency * 0.5),
            "last_run_date": rs[-1]["race_date"], "h2h_capped_to": None,
            "consistency": consistency,
        }

    # head-to-head cap: at a horse's most recent start, it cannot out-rate a
    # horse that finished in front of it (winner franks the form), give or take
    # weight-for-weight. Iterate to a fixpoint over the recent-race graph.
    race_class = {(r["race_date"], r["track_slug"], r["race_number"]): None for r in runs}
    for row in store.connection.execute(
        "SELECT DISTINCT race_date, track_slug, race_number, race_class FROM race_results"):
        k = (row["race_date"], row["track_slug"], row["race_number"])
        if k in race_class:
            race_class[k] = row["race_class"]
    weight_by_run = {(r["race_date"], r["track_slug"], r["race_number"], r["runner_number"]): None for r in runs}
    for row in store.connection.execute(
        "SELECT race_date, track_slug, race_number, runner_number, weight_carried_kg FROM runner_results"):
        k = (row["race_date"], row["track_slug"], row["race_number"], row["runner_number"])
        if k in weight_by_run:
            weight_by_run[k] = row["weight_carried_kg"]

    last_race_field: dict[str, list] = defaultdict(list)
    for r in runs:
        last_race_field[r["horse_key"]].append(r)
    caps: list[tuple[str, str, float]] = []   # (loser_key, winner_key, weight_relief)
    for key, rs in last_race_field.items():
        last = rs[-1]
        age = (cutoff - date.fromisoformat(last["race_date"])).days
        if age > H2H_CAP_MAX_AGE_DAYS or last["finish_position"] == 1:
            continue
        rk = (last["race_date"], last["track_slug"], last["race_number"])
        my_w = weight_by_run.get((*rk, last["runner_number"]))
        factor = _weight_factor(race_class.get(rk))
        for other in runs:
            if (other["race_date"], other["track_slug"], other["race_number"]) != rk:
                continue
            if other["horse_key"] == key or other["finish_position"] is None:
                continue
            if other["finish_position"] < last["finish_position"]:
                ow = weight_by_run.get((*rk, other["runner_number"]))
                relief = ((float(my_w) - float(ow)) * factor) if (my_w is not None and ow is not None) else 0.0
                caps.append((key, other["horse_key"], max(0.0, relief)))

    for _ in range(4):
        changed = False
        for loser, winner, relief in caps:
            if loser not in states or winner not in states:
                continue
            ceiling = states[winner]["overall_rating"] + relief - H2H_CAP_EPSILON
            if states[loser]["overall_rating"] > ceiling:
                states[loser]["h2h_capped_to"] = round(ceiling, 2)
                states[loser]["overall_rating"] = ceiling
                changed = True
        if not changed:
            break

    now = utc_now()
    for s in states.values():
        detail = {"reliability": round(s["reliability"], 3), "consistency": round(s["consistency"], 2),
                  "recency_half_life_days": RECENCY_HALF_LIFE_DAYS,
                  "h2h_capped": s["h2h_capped_to"] is not None}
        store.connection.execute(
            """INSERT INTO par_v2_horse_rating_states VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (STATE_MODEL_VERSION, as_of_date, s["horse_key"], s["horse_name"],
             s["overall_rating"], s["peak_rating"], s["recent_rating"], s["rated_runs"],
             s["reliability"], s["uncertainty"], s["last_run_date"], s["h2h_capped_to"],
             json.dumps(detail, sort_keys=True), now))
    store.connection.commit()
    return {"model_version": STATE_MODEL_VERSION, "as_of_date": as_of_date,
            "horses_rated": len(states), "h2h_caps_applied": sum(1 for s in states.values() if s["h2h_capped_to"] is not None)}


# ── validation ─────────────────────────────────────────────────────────────

def _softmax(xs):
    m = max(xs); e = [math.exp(x - m) for x in xs]; s = sum(e)
    return [x / s for x in e]


def prediction_test(store: RacingStore, as_of_date: str, *, walk_forward: bool = True) -> dict[str, Any]:
    """DIAGNOSTIC ONLY — NOT A RATING GATE.

    This fits a softmax temperature over the ratings and scores log loss and
    top-pick strike. That is a PRICING-layer proxy: it measures
    ratings -> probabilities -> picks, and the conversion step is not part of the
    rating. It misjudges a rating in both directions — a well-ordered rating can
    fail because one global temperature cannot map ratings to probabilities
    across field sizes, distances and class (the engine's own note: "temperature
    maxed the grid"), and a flat rating can pass by being calibrated in aggregate
    while ordering fields badly.

    THIS IS A HORSE RATING ENGINE. Judge it with racing_engine.rating_quality:
    concordance on prior form, run-to-run repeatability, margin calibration and
    scale. Win probability, strike rate and ROI belong to the Pricing Engine
    (build plan stage 6 — "no profit claim is permitted from ratings alone").

    Kept because it is a useful early read on whether the ratings will survive
    the pricing layer. Never use it to promote or reject a rating.

    v3.1 franked run figures vs par-v2 vs uniform, frozen naive protocol.

    WALK-FORWARD (default, and the only honest setting).
    Franking revises a race once its beaten field runs again, so a 2024 run's
    franked figure contains 2025-26 form. Scoring a 2025 race with that figure
    leaks the future: `prior()` filters the run DATES correctly, but the run
    VALUES already knew what happened next. That is the increment-9 promotion
    blocker, and it is why the headline 18.2% strike was optimistic.

    With walk_forward=True a run contributes its franked figure only if the
    franking was knowable before the race being predicted
    (`frank_effective_from < race_date`); otherwise it contributes its unfranked
    par-v2 base. Pass walk_forward=False only to reproduce the old, leaky number
    for comparison — never to justify a promotion.
    """
    def history(table, model, extra=""):
        h = defaultdict(list)
        for row in store.connection.execute(
            f"SELECT race_date, horse_key, performance_rating FROM {table} "
            f"WHERE model_version=? AND as_of_date=? {extra} ORDER BY race_date", (model, as_of_date)):
            h[row["horse_key"]].append((row["race_date"], float(row["performance_rating"])))
        return h

    def franked_history_effective():
        """(race_date, base, franked, effective_from) per horse."""
        h = defaultdict(list)
        for row in store.connection.execute(
            """SELECT race_date, horse_key, par_v2_figure, performance_rating, frank_effective_from
                 FROM franked_run_performances WHERE model_version=? AND as_of_date=?
                ORDER BY race_date""", (RUN_MODEL_VERSION, as_of_date)):
            h[row["horse_key"]].append((row["race_date"], float(row["par_v2_figure"]),
                                        float(row["performance_rating"]), row["frank_effective_from"]))
        return h

    v31_eff = franked_history_effective()
    v31 = history("franked_run_performances", RUN_MODEL_VERSION)
    pv2 = history("par_run_performances", PAR_V2_MODEL)
    races = store.connection.execute(
        """SELECT DISTINCT race_date, track_slug, race_number FROM franked_run_performances
            WHERE model_version=? AND as_of_date=? AND race_date >= '2024-01-01'
            ORDER BY race_date""", (RUN_MODEL_VERSION, as_of_date)).fetchall()

    def prior(h, k, day):
        vals = [v for d, v in h.get(k, []) if d < day]
        return statistics.median(vals[-3:]) if vals else 100.0

    def prior_walk_forward(k, day):
        """Median of the horse's last 3 runs as the figures stood on `day`:
        franked only where the franking evidence predates the race."""
        vals = [(franked if (eff is not None and eff < day) else base)
                for d, base, franked, eff in v31_eff.get(k, []) if d < day]
        return statistics.median(vals[-3:]) if vals else 100.0

    examples = []
    for rc in races:
        rows = store.connection.execute(
            """SELECT horse_key, finish_position FROM franked_run_performances
                WHERE model_version=? AND as_of_date=? AND race_date=? AND track_slug=? AND race_number=?
                  AND finish_position IS NOT NULL ORDER BY runner_number""",
            (RUN_MODEL_VERSION, as_of_date, rc["race_date"], rc["track_slug"], rc["race_number"])).fetchall()
        if len(rows) < 4 or sum(x["finish_position"] == 1 for x in rows) != 1:
            continue
        keys = [x["horse_key"] for x in rows]
        winner = next(i for i, x in enumerate(rows) if x["finish_position"] == 1)
        cov = lambda h: sum(any(d < rc["race_date"] for d, _ in h.get(k, [])) for k in keys) / len(keys)
        if min(cov(v31), cov(pv2)) < 0.60:
            continue
        examples.append({"date": rc["race_date"], "winner": winner, "field": len(keys),
                         "v31": [(prior_walk_forward(k, rc["race_date"]) if walk_forward
                                  else prior(v31, k, rc["race_date"])) for k in keys],
                         "v31_leaky": [prior(v31, k, rc["race_date"]) for k in keys],
                         "pv2": [prior(pv2, k, rc["race_date"]) for k in keys]})

    train = [e for e in examples if e["date"] < "2025-01-01"]
    test = [e for e in examples if e["date"] >= "2025-01-01"]
    temps = (3., 5., 8., 10., 12., 15.)

    def loss(rows, name, t):
        return statistics.mean(-math.log(max(_softmax([v / t for v in e[name]])[e["winner"]], 1e-12)) for e in rows)

    def metrics(name):
        t = min(temps, key=lambda tt: loss(train, name, tt))
        ll, hit = [], []
        for e in test:
            p = _softmax([v / t for v in e[name]]); w = e["winner"]
            ll.append(-math.log(max(p[w], 1e-12)))
            hit.append(int(max(range(len(p)), key=p.__getitem__) == w))
        return {"temperature": t, "mean_log_loss": statistics.mean(ll), "top_pick_strike_rate": statistics.mean(hit)}

    u = statistics.mean(math.log(e["field"]) for e in test)
    m31, mp2 = metrics("v31"), metrics("pv2")
    leaky = metrics("v31_leaky") if walk_forward else None
    out = {"train_races": len(train), "test_races": len(test),
           "protocol": "walk_forward_effective_dated" if walk_forward else "LEAKY_as_of_franking",
           "par_v2": mp2, "form_first_v3_1": m31, "uniform_log_loss": u,
           "v3_1_beats_uniform": m31["mean_log_loss"] < u,
           "v3_1_beats_par_v2": m31["mean_log_loss"] < mp2["mean_log_loss"]}
    if leaky is not None:
        # Kept visible on purpose: the gap between these two IS the leakage, and
        # the old headline number came from the leaky column.
        out["form_first_v3_1_leaky_for_comparison"] = leaky
        out["leakage_log_loss_overstatement"] = leaky["mean_log_loss"] - m31["mean_log_loss"]
        out["leakage_strike_overstatement"] = (leaky["top_pick_strike_rate"]
                                               - m31["top_pick_strike_rate"])
    return out


def run(store: RacingStore, as_of_date: str) -> dict[str, Any]:
    a = build_franked_runs(store, as_of_date)
    b = build_horse_ratings(store, as_of_date)
    return {"franked_runs": a, "horse_ratings": b}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--horses", nargs="*", default=[])
    args = ap.parse_args()
    store = RacingStore(args.database)
    try:
        report = run(store, args.as_of)
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.test:
            print("\n=== naive predictive gate (v3.1 vs par-v2 vs uniform) ===")
            print(json.dumps(prediction_test(store, args.as_of), indent=2, sort_keys=True))
        for name in args.horses:
            row = store.connection.execute(
                """SELECT horse_name, overall_rating, peak_rating, recent_rating, rated_runs,
                          uncertainty, last_run_date, h2h_capped_to
                     FROM par_v2_horse_rating_states
                    WHERE model_version=? AND as_of_date=? AND lower(horse_name) LIKE ?""",
                (STATE_MODEL_VERSION, args.as_of, f"%{name.lower()}%")).fetchone()
            if row:
                print(f"\n{row['horse_name']}: overall {row['overall_rating']:.1f}  "
                      f"peak {row['peak_rating']:.1f}  last-run {row['recent_rating']:.1f}  "
                      f"({row['rated_runs']} runs, ±{row['uncertainty']:.1f}, "
                      f"last {row['last_run_date']}"
                      + (f", H2H-capped to {row['h2h_capped_to']}" if row['h2h_capped_to'] else "") + ")")
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "franked_form_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
