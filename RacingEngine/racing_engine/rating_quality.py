"""
rating_quality.py — how good is a HORSE RATING, judged as a rating.

THIS IS A RATING ENGINE. It is not a tipping model and not a pricing model.
A rating answers "how good was that run / how good is that horse", on a scale
where a point means a consistent amount of merit. Turning ratings into win
probabilities is the Pricing Engine's job, later, and it will fold in barrier,
map, tempo, going, weight-for-the-day, jockey and market — with the rating as
roughly half the signal.

WHY THIS MODULE EXISTS
──────────────────────
The engine was being gated on `prediction_test`: fit a softmax temperature over
the ratings, then score log loss and top-pick strike rate. That is a *pricing*
test wearing a rating test's clothes, and it misjudges the rating in both
directions:

  * false negative — a well-ordered rating fails because one global temperature
    cannot map ratings to probabilities across field sizes, distances and class.
    The engine's own note records the symptom: "temperature maxed the grid — the
    optimiser wants to flatten the ratings almost entirely".
  * false positive — a flat rating can look acceptable in aggregate while
    ordering horses badly inside races, which is the only thing a rating does.

The build plan already draws this line: pricing is Stage 6, "no profit claim is
permitted from ratings alone". These are the Stage 1-5 metrics.

THE FOUR RATING GATES
─────────────────────
1. CONCORDANCE     Does what we knew BEFORE the race order the result? Pairwise,
                   no probability conversion, no fitted parameter.
                   Uses each horse's PRIOR figure (median of its last 3 runs
                   before the race), never the figure from the race itself: a run
                   figure is derived from that race's beaten margin, so scoring
                   it against that race's finishing order is circular and returns
                   ~0.84 for any margin-based model regardless of quality.
2. REPEATABILITY   Does a horse's figure predict its NEXT figure? The classic
                   Timeform / Ragozin criterion. A figure that does not repeat is
                   measuring the race, not the horse. Franking should IMPROVE
                   this — that is its whole claim.
3. MARGIN CALIBRATION  Does a gap in PRIOR ratings translate into the beaten
                   lengths the scale claims? Prior-based for the same reason:
                   regressing a run figure on the margin it was built from just
                   recovers the pounds-per-length constant.
4. SCALE           Can the scale express an elite run? Audit F1 found it
                   structurally could not reach 125+.

BASELINES
─────────
A concordance number means nothing on its own. 0.500 is a coin flip, and the
official handicapper's mark is free — if a model cannot beat the mark at ordering
a field, it is not yet earning its keep. `--baselines` scores, on exactly the same
races and pairs:

  coin_flip           0.500 by construction
  official_rating     the horse's official mark carried on the day
  last_start_figure   the horse's single most recent figure, no blending

Reference points, not pass marks: on PRIOR form a sound rating concords around
0.60-0.70, and repeats around 0.45-0.60 run to run. Ordering is the gate that
matters; the others describe the scale. Beware any concordance near 0.85+ — that
is the signature of scoring a run figure against its own race.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "v2_ratings"

# Where each model keeps its run figures. Every entry must expose
# race identity, horse_key, finish_position, beaten_lengths and a rating.
RATING_SOURCES = {
    "form-first-v2.0": {
        "table": "v2_run_performances", "rating": "performance_rating",
        "join": "JOIN v2_clean_races r USING(race_id) "
                "JOIN v2_clean_runner_results u ON u.race_id=p.race_id "
                "AND u.runner_number=p.runner_number",
        "race_id": "p.race_id", "date": "r.race_date",
        "finish": "u.finish_position", "beaten": "u.beaten_lengths",
        "distance": "r.distance_metres", "as_of": None,
    },
    "performance-par-v2.0": {
        "table": "par_run_performances", "rating": "performance_rating",
        "join": "", "race_id": "p.race_date || '|' || p.track_slug || '|' || p.race_number",
        "date": "p.race_date", "finish": "p.finish_position", "beaten": "p.beaten_lengths",
        "distance": "NULL", "as_of": "as_of_date",
    },
    "form-first-v3.1": {
        "table": "franked_run_performances", "rating": "performance_rating",
        "join": "", "race_id": "p.race_date || '|' || p.track_slug || '|' || p.race_number",
        "date": "p.race_date", "finish": "p.finish_position", "beaten": "p.beaten_lengths",
        "distance": "NULL", "as_of": "as_of_date",
    },
}


def _load(store: RacingStore, model: str, as_of_date: str | None) -> list[dict]:
    cfg = RATING_SOURCES[model]
    where = ["p.model_version = ?"]
    params: list[Any] = [model]
    if cfg["as_of"] and as_of_date:
        where.append(f"p.{cfg['as_of']} = ?"); params.append(as_of_date)
    sql = (f"SELECT {cfg['race_id']} AS race_id, {cfg['date']} AS race_date, "
           f"p.horse_key AS horse_key, {cfg['finish']} AS finish_position, "
           f"{cfg['beaten']} AS beaten_lengths, {cfg['distance']} AS distance_metres, "
           f"p.{cfg['rating']} AS rating "
           f"FROM {cfg['table']} p {cfg['join']} WHERE " + " AND ".join(where))
    return [dict(row) for row in store.connection.execute(sql, params)]


def _prior_index(rows: list[dict]) -> dict[str, list[tuple[str, float]]]:
    hist: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for r in rows:
        if r["rating"] is not None:
            hist[r["horse_key"]].append((r["race_date"], float(r["rating"])))
    for v in hist.values():
        v.sort()
    return hist


def _prior(hist, horse_key: str, day: str) -> float | None:
    vals = [v for d, v in hist.get(horse_key, []) if d < day]
    return statistics.median(vals[-3:]) if vals else None


def concordance(rows: list[dict]) -> dict[str, Any]:
    """Gate 1 — does PRIOR form order the finish? (never the race's own figure)"""
    hist = _prior_index(rows)
    races: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["finish_position"] is not None:
            prior = _prior(hist, r["horse_key"], r["race_date"])
            if prior is None:
                continue
            races[r["race_id"]].append({**r, "rating": prior})
    agree = disagree = tied = 0
    per_race = []
    for runners in races.values():
        if len(runners) < 3:
            continue
        a = d = 0
        for i in range(len(runners)):
            for j in range(i + 1, len(runners)):
                x, y = runners[i], runners[j]
                if x["finish_position"] == y["finish_position"]:
                    continue
                if x["rating"] == y["rating"]:
                    tied += 1; continue
                better_rated_won = ((x["rating"] > y["rating"]) ==
                                    (x["finish_position"] < y["finish_position"]))
                if better_rated_won: a += 1
                else: d += 1
        agree += a; disagree += d
        if a + d:
            per_race.append(a / (a + d))
    total = agree + disagree
    return {"pairs": total, "races": len(per_race), "ties": tied,
            "concordance": round(agree / total, 4) if total else None,
            "mean_race_concordance": round(statistics.mean(per_race), 4) if per_race else None}


def repeatability(rows: list[dict]) -> dict[str, Any]:
    """Gate 2 — does a horse's figure predict its next figure?"""
    hist: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for r in rows:
        if r["rating"] is not None:
            hist[r["horse_key"]].append((r["race_date"], float(r["rating"])))
    pairs = []
    for runs in hist.values():
        runs.sort()
        pairs.extend((runs[i][1], runs[i + 1][1]) for i in range(len(runs) - 1))
    if len(pairs) < 30:
        return {"pairs": len(pairs), "correlation": None}
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    mad = statistics.mean(abs(y - x) for x, y in pairs)
    return {"pairs": len(pairs), "correlation": round(num / den, 4) if den else None,
            "mean_abs_change_between_runs": round(mad, 2)}


def margin_calibration(rows: list[dict]) -> dict[str, Any]:
    """Gate 3 — does a PRIOR rating gap translate into the lengths claimed?"""
    hist = _prior_index(rows)
    obs = []
    races: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        prior = _prior(hist, r["horse_key"], r["race_date"])
        if prior is None:
            continue
        races[r["race_id"]].append({**r, "rating": prior})
    for runners in races.values():
        winner = next((x for x in runners if x["finish_position"] == 1), None)
        if winner is None or winner["rating"] is None:
            continue
        for x in runners:
            if x is winner or x["beaten_lengths"] is None or x["rating"] is None:
                continue
            gap = winner["rating"] - x["rating"]
            if 0 < gap < 40 and 0 < x["beaten_lengths"] < 30:
                obs.append((x["beaten_lengths"], gap))
    if len(obs) < 50:
        return {"observations": len(obs), "points_per_length": None}
    lx = [o[0] for o in obs]; ly = [o[1] for o in obs]
    mx, my = statistics.mean(lx), statistics.mean(ly)
    den = sum((x - mx) ** 2 for x in lx)
    slope = sum((x - mx) * (y - my) for x, y in obs) / den if den else None
    return {"observations": len(obs),
            "points_per_length": round(slope, 3) if slope else None,
            "note": "rating points implied per length beaten; compare with the "
                    "engine's pounds-per-length scale (3.0 at 1000m to 1.0 at 2800m)"}


def scale(rows: list[dict]) -> dict[str, Any]:
    """Gate 4 — can the scale express an elite run?"""
    vals = sorted(float(r["rating"]) for r in rows if r["rating"] is not None)
    if not vals:
        return {}
    def pct(p): return vals[min(len(vals) - 1, int(p * len(vals)))]
    return {"n": len(vals), "min": round(vals[0], 1), "p5": round(pct(0.05), 1),
            "median": round(pct(0.50), 1), "p95": round(pct(0.95), 1),
            "max": round(vals[-1], 1),
            "runs_over_120": sum(1 for v in vals if v > 120),
            "runs_over_125": sum(1 for v in vals if v > 125)}


def _baseline_rows(store: RacingStore) -> list[dict]:
    """Official mark + finishing detail for every finished runner."""
    return [dict(r) for r in store.connection.execute(
        """SELECT p.race_id AS race_id, r.race_date AS race_date, u.horse_key AS horse_key,
                  u.finish_position AS finish_position, u.beaten_lengths AS beaten_lengths,
                  u.official_handicap_rating AS official_rating
             FROM v2_run_performances p
             JOIN v2_clean_races r USING(race_id)
             JOIN v2_clean_runner_results u
               ON u.race_id=p.race_id AND u.runner_number=p.runner_number
            WHERE p.model_version='form-first-v2.0' AND u.result_status='finished'""")]


def baselines(store: RacingStore, rows: list[dict]) -> dict[str, Any]:
    """What does doing nothing score on the same gate?"""
    out: dict[str, Any] = {"coin_flip_concordance": 0.5}

    # official mark — carried on the day, no prior lookup needed
    off = [{**r, "rating": r["official_rating"]}
           for r in _baseline_rows(store) if r["official_rating"] is not None]
    races: dict[str, list[dict]] = defaultdict(list)
    for r in off:
        if r["finish_position"] is not None:
            races[r["race_id"]].append(r)
    agree = disagree = 0
    for runners in races.values():
        if len(runners) < 3:
            continue
        for i in range(len(runners)):
            for j in range(i + 1, len(runners)):
                x, y = runners[i], runners[j]
                if x["finish_position"] == y["finish_position"] or x["rating"] == y["rating"]:
                    continue
                if (x["rating"] > y["rating"]) == (x["finish_position"] < y["finish_position"]):
                    agree += 1
                else:
                    disagree += 1
    out["official_rating_concordance"] = round(agree / (agree + disagree), 4) if agree + disagree else None
    out["official_rating_pairs"] = agree + disagree

    # last-start figure only — no median-of-3 blending
    hist = _prior_index(rows)
    def last_only(k, day):
        vals = [v for d, v in hist.get(k, []) if d < day]
        return vals[-1] if vals else None
    races2: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["finish_position"] is None:
            continue
        v = last_only(r["horse_key"], r["race_date"])
        if v is not None:
            races2[r["race_id"]].append({**r, "rating": v})
    a2 = d2 = 0
    for runners in races2.values():
        if len(runners) < 3:
            continue
        for i in range(len(runners)):
            for j in range(i + 1, len(runners)):
                x, y = runners[i], runners[j]
                if x["finish_position"] == y["finish_position"] or x["rating"] == y["rating"]:
                    continue
                if (x["rating"] > y["rating"]) == (x["finish_position"] < y["finish_position"]):
                    a2 += 1
                else:
                    d2 += 1
    out["last_start_figure_concordance"] = round(a2 / (a2 + d2), 4) if a2 + d2 else None
    return out


# ── how should a horse's prior runs be aggregated into "what we knew"? ──────
# Last-start-only beat median-of-3 on the ordering gate using identical figures,
# so the aggregation is doing real damage and is worth testing directly rather
# than assumed. Each of these is scored on exactly the same races and pairs.
AGGREGATORS = {
    "last_start_only":      lambda v: v[-1],
    "median_last_2":        lambda v: statistics.median(v[-2:]),
    "median_last_3":        lambda v: statistics.median(v[-3:]),
    "median_last_5":        lambda v: statistics.median(v[-5:]),
    "mean_last_3":          lambda v: statistics.mean(v[-3:]),
    "max_last_3":           lambda v: max(v[-3:]),
    "peak_career":          lambda v: max(v),
    "weighted_recent_3":    lambda v: (sum(w * x for w, x in zip((3, 2, 1), reversed(v[-3:])))
                                       / sum((3, 2, 1)[:len(v[-3:])])),
    "best_of_last_2":       lambda v: max(v[-2:]),
}


def aggregation_test(rows: list[dict]) -> dict[str, Any]:
    """Which way of turning past runs into 'what we knew' orders a field best?"""
    hist = _prior_index(rows)
    finished = [r for r in rows if r["finish_position"] is not None]
    out = {}
    for name, fn in AGGREGATORS.items():
        races: dict[str, list[dict]] = defaultdict(list)
        for r in finished:
            vals = [v for d, v in hist.get(r["horse_key"], []) if d < r["race_date"]]
            if vals:
                races[r["race_id"]].append({**r, "rating": fn(vals)})
        a = d = 0
        for runners in races.values():
            if len(runners) < 3:
                continue
            for i in range(len(runners)):
                for j in range(i + 1, len(runners)):
                    x, y = runners[i], runners[j]
                    if x["finish_position"] == y["finish_position"] or x["rating"] == y["rating"]:
                        continue
                    if (x["rating"] > y["rating"]) == (x["finish_position"] < y["finish_position"]):
                        a += 1
                    else:
                        d += 1
        out[name] = {"concordance": round(a / (a + d), 4) if a + d else None, "pairs": a + d}
    return out


def segmented_concordance(store: RacingStore, rows: list[dict]) -> dict[str, Any]:
    """Where does the ordering fail? Concordance split by class, distance,
    field size and state — a single number hides which races it cannot read."""
    meta = {r["race_id"]: dict(r) for r in store.connection.execute(
        "SELECT race_id, class_family, distance_metres, state FROM v2_clean_races")}
    hist = _prior_index(rows)
    races: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["finish_position"] is None:
            continue
        pr = _prior(hist, r["horse_key"], r["race_date"])
        if pr is not None:
            races[r["race_id"]].append({**r, "rating": pr})

    def bucket_distance(d):
        if not d: return "unknown"
        return "1000-1200" if d <= 1200 else "1300-1600" if d <= 1600 else "1700-2000" if d <= 2000 else "2000+"

    tallies: dict[str, dict[str, list[int]]] = {k: defaultdict(lambda: [0, 0])
                                                for k in ("class", "distance", "field_size", "state")}
    for rid, runners in races.items():
        if len(runners) < 3:
            continue
        m = meta.get(rid, {})
        keys = {"class": m.get("class_family") or "unknown",
                "distance": bucket_distance(m.get("distance_metres")),
                "field_size": "small (<8)" if len(runners) < 8 else "medium (8-11)" if len(runners) < 12 else "large (12+)",
                "state": m.get("state") or "unknown"}
        a = d = 0
        for i in range(len(runners)):
            for j in range(i + 1, len(runners)):
                x, y = runners[i], runners[j]
                if x["finish_position"] == y["finish_position"] or x["rating"] == y["rating"]:
                    continue
                if (x["rating"] > y["rating"]) == (x["finish_position"] < y["finish_position"]): a += 1
                else: d += 1
        for dim, key in keys.items():
            tallies[dim][key][0] += a; tallies[dim][key][1] += d
    return {dim: {k: {"concordance": round(v[0] / (v[0] + v[1]), 4) if v[0] + v[1] else None,
                      "pairs": v[0] + v[1]}
                  for k, v in sorted(t.items())} for dim, t in tallies.items()}


def evaluate(store: RacingStore, model: str, as_of_date: str | None = None,
             with_baselines: bool = False) -> dict[str, Any]:
    rows = _load(store, model, as_of_date)
    result = {"model_version": model, "as_of_date": as_of_date, "runs": len(rows),
            "concordance": concordance(rows), "repeatability": repeatability(rows),
            "margin_calibration": margin_calibration(rows), "scale": scale(rows),
            "note": "Rating-layer metrics only. Win probability, strike rate and ROI "
                    "belong to the Pricing Engine (build plan stage 6)."}
    if with_baselines:
        result["baselines"] = baselines(store, rows)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="form-first-v2.0", choices=sorted(RATING_SOURCES))
    ap.add_argument("--as-of", dest="as_of", default=None)
    ap.add_argument("--compare", nargs="*", default=None,
                    help="evaluate several models side by side")
    ap.add_argument("--segments", action="store_true",
                    help="split concordance by class, distance, field size and state")
    ap.add_argument("--aggregation", action="store_true",
                    help="compare ways of turning past runs into a prior")
    ap.add_argument("--baselines", action="store_true",
                    help="also score the coin flip, the official mark and last-start-only")
    args = ap.parse_args()

    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        models = args.compare if args.compare else [args.model]
        results = {}
        for m in models:
            try:
                results[m] = evaluate(store, m, args.as_of, with_baselines=args.baselines)
            except Exception as exc:
                results[m] = {"error": str(exc)}
        print(f"{'model':<26}{'runs':>8}{'concord':>9}{'repeat':>8}{'pts/len':>9}{'p5':>7}{'p95':>7}{'max':>7}")
        for m, r in results.items():
            if "error" in r:
                print(f"{m:<26}  ERROR: {r['error'][:60]}"); continue
            c = r["concordance"]; rp = r["repeatability"]; mc = r["margin_calibration"]; sc = r["scale"]
            print(f"{m:<26}{r['runs']:>8}{(c['concordance'] or 0):>9.4f}"
                  f"{(rp['correlation'] or 0):>8.3f}{(mc['points_per_length'] or 0):>9.3f}"
                  f"{sc.get('p5',0):>7.1f}{sc.get('p95',0):>7.1f}{sc.get('max',0):>7.1f}")
        if args.segments:
            for m in models:
                rows = _load(store, m, args.as_of)
                seg = segmented_concordance(store, rows)
                for dim, vals in seg.items():
                    print(f"\n  concordance by {dim}:")
                    for k, v in sorted(vals.items(), key=lambda kv: -(kv[1]["concordance"] or 0)):
                        if v["pairs"] < 500: continue
                        print(f"    {k:<16} {v['concordance']:.4f}   ({v['pairs']:,} pairs)")
                results.setdefault(m, {})["segments"] = seg

        if args.aggregation:
            for m in models:
                rows = _load(store, m, args.as_of)
                agg = aggregation_test(rows)
                print(f"\n  prior aggregation — {m} (same races, same pairs):")
                for name, v in sorted(agg.items(), key=lambda kv: -(kv[1]["concordance"] or 0)):
                    print(f"    {name:<20} {v['concordance']:.4f}   ({v['pairs']:,} pairs)")
                results.setdefault(m, {})["aggregation"] = agg

        for m, r in results.items():
            if "baselines" in r:
                b = r["baselines"]
                print(f"\n  baselines on the same races:")
                print(f"    coin flip          {b['coin_flip_concordance']:.4f}")
                print(f"    official mark      {b['official_rating_concordance']}")
                print(f"    last start only    {b['last_start_figure_concordance']}")
                break
        OUTPUT.mkdir(parents=True, exist_ok=True)
        out = OUTPUT / "rating_quality.json"
        out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nwritten: {out.relative_to(ROOT)}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
