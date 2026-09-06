"""form-first-v3.0 — form + speed dual rating with pace-aware race levels.

Built 2026-09-06 off the `rating_system_audit_2026-09.md` findings. Four changes
over `form-first-v2.0`:

  1. FORM + SPEED DUAL RATING. The par/time figure (`performance-par-v1.0`,
     going-aware) is promoted from "the model we compare against" to a co-equal
     input. Scales are aligned first, then blended SPEED_W / (1-SPEED_W).
     Disagreement between the two lowers confidence.
  2. PACE FOLDED INTO THE LEVEL. `v2_race_pace_shapes` + `v2_runner_pace_ratings`
     neutralise the collateral anchors, so a front-running steal in a slow race
     no longer inflates the race level, and anti-suited beaten horses in a false
     tempo are not over-penalised.
  3. COMPRESSION FIX. `class_standard` becomes a one-sided stabiliser: a strong
     field (collateral >= standard) keeps ~all of its collateral; only a
     weak/thin field is pulled up toward the standard. Removes the downward drag
     on elite performances.
  4. VARIABLE POUNDS-PER-LENGTH. base(distance) x going x tempo, not distance
     alone. Softer ground and false tempo discount beaten-length penalties.

This module does NOT price races or place bets. It is the horse-rating input to
a later race-betting engine that will combine it with tempo / map / race-strength
/ barrier / jockey / trainer / intent. No prediction gate is applied here — the
audit showed a rating-only chronological test is near-uninformative; validation
happens at the pricing-engine layer against market prices.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .horse_identity import identity_key
from .storage import RacingStore
from .v2_ratings import CLASS_STANDARDS, class_family, pounds_per_length

ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "form-first-v3.0"
PAR_MODEL = "performance-par-v1.0"
OUTPUT = ROOT / "reports" / "v2_ratings"

# ── Tunables (the pricing engine, not this module, validates these) ───────────
SPEED_LIFT_W = 0.35        # LIFT-ONLY blend. A fast raw time is hard to fake, so
                          # the speed figure can push a run UP when it exceeds
                          # the form figure; it is NOT allowed to cut it, because
                          # performance-par-v1.0 has no pace adjustment and a
                          # slow-run tactical WFA race produces a meaningless low
                          # time figure. When a pace/weight/class-adjusted
                          # performance-par-v2.0 exists, switch this to a proper
                          # two-way blend.
SPEED_PLAUSIBLE = (40.0, 140.0)
SPEED_WEIGHT_PTS_PER_KG = 0.8   # par-v1 carries NO weight adjustment, so it
                               # over-rates light-weight handicappers who post
                               # fast raw times. Add merit back for weight
                               # carried vs the winner. A proper weight/class/
                               # pace pass belongs in performance.py (par-v2).
PACE_ANCHOR_CAP = 3.0       # max pace adjustment folded into a collateral anchor
PACE_RUNNER_CAP = 2.5       # max pace adjustment on an individual run
GOING_PPL_MULT = {"firm": 1.05, "good": 1.00, "soft": 0.92, "heavy": 0.85,
                  "synthetic": 1.00}
FALSE_TEMPO_LABELS = {"sprint_home", "very_slow_early", "slow_early", "pace_collapse"}
FALSE_TEMPO_PPL_CUT = 0.30  # up to a 30% ppl cut in a clearly false-tempo race
MARGIN_KNEE = 4.0           # beaten-length credit is linear to here, then
MARGIN_TAPER = 0.45         # taxed — a 9L rout is not 9/4 as informative about
                            # the winner as a 4L win (F2 in the audit).
# Weight → MERIT, not the handicapper's policy scale. 2.2 pts/kg is what the
# handicapper uses to SET weights (assumes weight converts 1:1 to performance);
# the measured performance effect is far smaller — high-class horses carry big
# weights and still win. And in WFA / set-weights races the weight difference is
# an age/sex allowance, not merit, so it must be near-zero. Without this a mare's
# conqueror out-rates her for carrying the 2 kg sex allowance.
WEIGHT_MERIT_PTS_PER_KG_HCP = 0.9
WEIGHT_MERIT_PTS_PER_KG_WFA = 0.2


def _weight_pts_per_kg(race_class: str | None) -> float:
    t = (race_class or "").lower()
    if "weight for age" in t or "wfa" in t or "set weight" in t or "standard weight" in t:
        return WEIGHT_MERIT_PTS_PER_KG_WFA
    return WEIGHT_MERIT_PTS_PER_KG_HCP


def _effective_margin(margin: float) -> float:
    if margin <= MARGIN_KNEE:
        return margin
    return MARGIN_KNEE + (margin - MARGIN_KNEE) * MARGIN_TAPER


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def going_bucket(text: str | None) -> str:
    t = (text or "").lower()
    for key in ("synthetic", "tapeta", "poly"):
        if key in t:
            return "synthetic"
    if "heavy" in t:
        return "heavy"
    if "soft" in t:
        return "soft"
    if "firm" in t or "fine" in t:
        return "firm"
    return "good"


def schema(store: RacingStore) -> None:
    store.connection.execute("""
    CREATE TABLE IF NOT EXISTS v3_run_performances (
      model_version TEXT NOT NULL, race_id TEXT NOT NULL, runner_number INTEGER NOT NULL,
      horse_key TEXT NOT NULL, horse_name TEXT NOT NULL,
      performance_rating REAL NOT NULL, form_figure REAL NOT NULL,
      speed_figure REAL, race_strength REAL NOT NULL,
      margin_component REAL NOT NULL, weight_component REAL NOT NULL,
      pace_component REAL NOT NULL, class_standard REAL NOT NULL,
      anchor_coverage REAL NOT NULL, speed_blended INTEGER NOT NULL,
      confidence REAL NOT NULL, detail_json TEXT NOT NULL,
      PRIMARY KEY (model_version, race_id, runner_number)
    )""")
    store.connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_v3_horse ON v3_run_performances(model_version, horse_key)")
    store.connection.commit()


# ── Speed-figure scale alignment ─────────────────────────────────────────────

def _load_speed_figures(store: RacingStore) -> dict[tuple[str, str, str, int, int], float]:
    """(source, race_date, track_slug, race_number, runner_number) -> par-v1 rating.

    Keyed by source because NSW race numbers collide across sources (the
    rnsw-authorised card and the racing-com-nsw-authorised-v2 card number races
    differently). v2_clean_races records which source it used; match that.
    """
    out: dict[tuple[str, str, str, int, int], float] = {}
    for row in store.connection.execute(
        """SELECT source, race_date, track_slug, race_number, runner_number, performance_rating
             FROM run_performances WHERE model_version=? AND performance_rating IS NOT NULL""",
        (PAR_MODEL,)):
        v = float(row["performance_rating"])
        if SPEED_PLAUSIBLE[0] <= v <= SPEED_PLAUSIBLE[1]:
            out[(row["source"], row["race_date"], row["track_slug"], int(row["race_number"]),
                 int(row["runner_number"]))] = v
    return out


def _fit_alignment(form_values: list[float], speed_values: list[float]) -> tuple[float, float]:
    """speed_aligned = a + b*speed_raw.

    Robust: match the p20 and p85 quantiles (not mean/sd — the speed figure has
    a genuinely narrower spread than a form figure, and mean/sd matching would
    over-stretch its fat top tail). b is clamped to [0.75, 1.35] so a fast time
    can lift a run but not blow the scale open.
    """
    if len(speed_values) < 100:
        return 0.0, 1.0
    def q(values, frac):
        s = sorted(values)
        return s[max(0, min(len(s) - 1, int(frac * len(s))))]
    f20, f85 = q(form_values, 0.20), q(form_values, 0.85)
    s20, s85 = q(speed_values, 0.20), q(speed_values, 0.85)
    b = (f85 - f20) / (s85 - s20) if s85 != s20 else 1.0
    b = max(0.75, min(1.35, b))
    fmed, smed = q(form_values, 0.50), q(speed_values, 0.50)
    a = fmed - b * smed
    return a, b


# ── Pace ────────────────────────────────────────────────────────────────────

_PACE_VERSION_ORDER = ("pace-shape-v2.0-shadow", "pace-shape-v2.1-pit-shadow")  # later wins


def _load_pace(store: RacingStore):
    shapes: dict[str, dict] = {}
    for ver in _PACE_VERSION_ORDER:                    # newest version overwrites
        for row in store.connection.execute(
            "SELECT race_id, pace_label, confidence FROM v2_race_pace_shapes WHERE version=?", (ver,)):
            shapes[row["race_id"]] = {"label": row["pace_label"], "conf": float(row["confidence"] or 0.0)}
    runners: dict[tuple[str, int], float] = {}
    for ver in _PACE_VERSION_ORDER:
        for row in store.connection.execute(
            "SELECT race_id, runner_number, shadow_rating_adjustment FROM v2_runner_pace_ratings WHERE version=?", (ver,)):
            if row["shadow_rating_adjustment"] is not None:
                runners[(row["race_id"], int(row["runner_number"]))] = float(row["shadow_rating_adjustment"])
    return shapes, runners


def _going_lookup(store: RacingStore) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in store.connection.execute(
        """SELECT r.race_id, rr.track_condition
             FROM v2_clean_races r JOIN race_results rr
               ON rr.source=r.source AND rr.race_date=r.race_date
              AND rr.track_slug=r.track_slug AND rr.race_number=r.race_number"""):
        out[row["race_id"]] = going_bucket(row["track_condition"])
    return out


# ── Build ───────────────────────────────────────────────────────────────────

def _previous_form(cache: dict[str, list[float]], horse_key: str) -> float | None:
    """Median of the horse's last 3 v3 figures, from an in-memory chronological
    cache the build fills race-by-race (no lookahead — a race is only added
    after it is written)."""
    hist = cache.get(horse_key)
    return statistics.median(hist[-3:]) if hist else None


def build(store: RacingStore) -> dict[str, Any]:
    schema(store)
    # Bulk-build speed-ups; safe because a crash just means re-running build().
    store.connection.execute("PRAGMA synchronous=OFF")
    store.connection.execute("PRAGMA temp_store=MEMORY")
    store.connection.execute("DELETE FROM v3_run_performances WHERE model_version=?", (MODEL_VERSION,))

    speed = _load_speed_figures(store)
    shapes, runner_pace = _load_pace(store)
    going = _going_lookup(store)

    races = store.connection.execute(
        "SELECT * FROM v2_clean_races ORDER BY race_date, track_slug, race_number").fetchall()

    # Pass 1 — form figures only, to fit the speed alignment.
    pass1_form: dict[tuple[str, int], float] = {}
    align_form, align_speed = [], []
    counts: Counter[str] = Counter()
    prior_cache: dict[str, list[float]] = {}   # horse_key -> chronological v3 figures

    def race_form(race, for_alignment: bool):
        runners = store.connection.execute(
            """SELECT * FROM v2_clean_runner_results WHERE race_id=? AND result_status='finished'
                 AND finish_position IS NOT NULL AND finish_position < 90
                 ORDER BY finish_position""", (race["race_id"],)).fetchall()
        if len(runners) < 3:
            counts["too_few_finishers"] += 1
            return None
        winner = next((r for r in runners if r["finish_position"] == 1), None)
        if winner is None:
            counts["no_winner"] += 1
            return None
        distance = int(race["distance_metres"] or 1600)
        g = going.get(race["race_id"], "good")
        shape = shapes.get(race["race_id"])
        wpk = _weight_pts_per_kg(race["race_class"])
        ppl = pounds_per_length(distance) * GOING_PPL_MULT.get(g, 1.0)
        tempo_note = "neutral"
        if shape and shape["label"] in FALSE_TEMPO_LABELS:
            ppl *= 1.0 - FALSE_TEMPO_PPL_CUT * shape["conf"]
            tempo_note = f"false_tempo:{shape['label']}"
        elif shape is None:
            # No sectionals — the tempo is unverifiable, so a big winning margin
            # cannot be confirmed as earned. Haircut all margin effects 10%.
            ppl *= 0.90
            tempo_note = "tempo_unverified"

        winner_weight = float(winner["weight_carried_kg"] or 58.0)
        standard = CLASS_STANDARDS[class_family(race["race_class"], race["class_family"])]

        anchors = [r for r in runners if int(r["finish_position"]) <= 4]
        candidates = []
        for r in anchors:
            prior = (float(r["official_handicap_rating"]) if r["official_handicap_rating"]
                     else _previous_form(prior_cache, r["horse_key"]))
            if prior is None:
                continue
            margin = 0.0 if int(r["finish_position"]) == 1 else float(r["beaten_lengths"] or 0.0)
            wdelta = (winner_weight - float(r["weight_carried_kg"] or winner_weight)) * wpk
            pace_adj = 0.0
            rp = runner_pace.get((race["race_id"], int(r["runner_number"])))
            if rp is not None:
                pace_adj = max(-PACE_ANCHOR_CAP, min(PACE_ANCHOR_CAP, rp))
            candidates.append(prior + _effective_margin(margin) * ppl + wdelta + pace_adj)

        coverage = len(candidates) / len(anchors) if anchors else 0.0
        pace_verified = shape is not None and shape["label"] not in FALSE_TEMPO_LABELS
        if candidates:
            collateral = statistics.median(candidates)
            # COMPRESSION FIX: the class standard is a LOW-COVERAGE STABILISER
            # only — it stabilises a thin / poorly-anchored field, it does not
            # pull a well-anchored field (strong OR weak) toward a fixed par.
            # That removes both the downward drag on elite runs and the upward
            # inflation of moderate ones.
            full = 0.92 if pace_verified else 0.84     # a verified-tempo field earns full trust
            if coverage >= 0.60:
                w = full
            else:
                w = full * (coverage / 0.60)           # thin field leans on the standard
            strength = w * collateral + (1 - w) * standard
        else:
            collateral, w, strength = None, 0.0, standard

        rows_out = []
        for r in runners:
            margin = 0.0 if int(r["finish_position"]) == 1 else float(r["beaten_lengths"] or 0.0)
            weight_component = (float(r["weight_carried_kg"] or winner_weight) - winner_weight) * wpk
            margin_component = -_effective_margin(margin) * ppl
            pace_component = 0.0
            rp = runner_pace.get((race["race_id"], int(r["runner_number"])))
            if rp is not None:
                pace_component = max(-PACE_RUNNER_CAP, min(PACE_RUNNER_CAP, rp))
            form_figure = strength + margin_component + weight_component + pace_component
            rows_out.append({
                "race_id": race["race_id"], "runner_number": int(r["runner_number"]),
                "horse_key": r["horse_key"], "horse_name": r["horse_name"],
                "form_figure": form_figure, "race_strength": strength,
                "margin_component": margin_component, "weight_component": weight_component,
                "pace_component": pace_component, "class_standard": standard,
                "anchor_coverage": coverage, "collateral": collateral, "field_weight": w,
                "ppl": ppl, "going": g, "tempo_note": tempo_note,
                "finish_position": int(r["finish_position"]),
                "clock_status": race["clock_status"], "source": race["source"],
                "weight_kg": float(r["weight_carried_kg"] or winner_weight),
                "winner_weight_kg": winner_weight,
            })
        return rows_out

    for race in races:
        out = race_form(race, for_alignment=True)
        if not out:
            continue
        for row in out:
            pass1_form[(row["race_id"], row["runner_number"])] = row["form_figure"]
            d_, t_, n_ = row["race_id"].split("|")
            key = (row["source"], d_, t_, int(n_), row["runner_number"])
            if key in speed:
                align_form.append(row["form_figure"])
                align_speed.append(speed[key])

    a, b = _fit_alignment(align_form, align_speed)

    # Pass 2 — blend the speed figure; fill prior_cache race-by-race (no lookahead).
    prior_cache.clear()
    written = 0
    for race in races:
        out = race_form(race, for_alignment=False)
        if not out:
            continue
        race_v3: list[tuple[str, float]] = []
        for row in out:
            date_, track_, num_ = row["race_id"].split("|")
            key = (row["source"], date_, track_, int(num_), row["runner_number"])
            speed_raw = speed.get(key)
            speed_aligned = None
            blended = 0
            v3 = row["form_figure"]
            conf = 0.55 + 0.35 * row["anchor_coverage"] + (0.08 if row["clock_status"] == "valid" else 0.0)
            if speed_raw is not None:
                speed_aligned = a + b * speed_raw
                # par-v1 has no weight adjustment: a light-weight who posts a
                # fast raw time gets a flattering figure. Add merit back for
                # weight carried above the winner.
                speed_aligned += (row["weight_kg"] - row["winner_weight_kg"]) * SPEED_WEIGHT_PTS_PER_KG
                lift = max(0.0, speed_aligned - row["form_figure"])
                v3 = row["form_figure"] + SPEED_LIFT_W * lift
                conf *= max(0.75, 1.0 - lift / 60.0)
                blended = 1
            else:
                conf *= 0.85
            conf = min(0.92, conf)
            detail = {
                "method": "form + speed lift" if blended else "form only (no speed figure)",
                "speed_lift_w": SPEED_LIFT_W if blended else 0.0,
                "speed_alignment": {"a": round(a, 3), "b": round(b, 3)},
                "collateral": row["collateral"], "field_weight": round(row["field_weight"], 3),
                "class_standard": row["class_standard"], "ppl": round(row["ppl"], 3),
                "going": row["going"], "tempo": row["tempo_note"],
                "compression_fix": "one-sided class-par stabiliser",
            }
            store.connection.execute(
                """INSERT INTO v3_run_performances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (MODEL_VERSION, row["race_id"], row["runner_number"], row["horse_key"], row["horse_name"],
                 v3, row["form_figure"], speed_aligned, row["race_strength"],
                 row["margin_component"], row["weight_component"], row["pace_component"],
                 row["class_standard"], row["anchor_coverage"], blended, conf,
                 json.dumps(detail, sort_keys=True)))
            written += 1
            counts["performances"] += 1
            race_v3.append((row["horse_key"], v3))
        for hk, val in race_v3:
            prior_cache.setdefault(hk, []).append(val)
    store.connection.commit()

    return {"model_version": MODEL_VERSION, "runs_rated": written,
            "speed_alignment": {"a": round(a, 3), "b": round(b, 3), "pairs": len(align_speed)},
            "counts": dict(counts)}


def leaderboard(store: RacingStore, since: str, limit: int = 25) -> list[dict[str, Any]]:
    rows = store.connection.execute(
        """SELECT p.horse_name, p.performance_rating, p.form_figure, p.speed_figure,
                  p.speed_blended, p.confidence, r.race_date, r.track_slug, r.race_number,
                  r.distance_metres, r.class_family, cr.finish_position, cr.beaten_lengths,
                  (SELECT performance_rating FROM v2_run_performances v2
                    WHERE v2.model_version='form-first-v2.0' AND v2.race_id=p.race_id
                      AND v2.runner_number=p.runner_number) AS v2
             FROM v3_run_performances p JOIN v2_clean_races r USING(race_id)
             JOIN v2_clean_runner_results cr ON cr.race_id=p.race_id AND cr.runner_number=p.runner_number
            WHERE p.model_version=? AND r.race_date >= ?
            ORDER BY p.performance_rating DESC LIMIT ?""", (MODEL_VERSION, since, limit)).fetchall()
    return [dict(r) for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    ap.add_argument("--since", default="2023-09-06", help="leaderboard start date")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    store = RacingStore(args.database)
    try:
        report = build(store)
        print(json.dumps(report, indent=2, sort_keys=True))
        print(f"\nTOP {args.top} form-first-v3.0 RUNS since {args.since}")
        print(f"{'horse':<20}{'v3':>7}{'v2':>7}{'form':>7}{'speed':>7}  {'race':<30}{'fin':>4}")
        for x in leaderboard(store, args.since, args.top):
            sp = f"{x['speed_figure']:.1f}" if x['speed_figure'] is not None else "  –"
            v2 = f"{x['v2']:.1f}" if x['v2'] is not None else "  –"
            tr = x['track_slug'].replace('sportsbet-sandown-hillside', 'sandown')
            print(f"{x['horse_name']:<20}{x['performance_rating']:>7.1f}{v2:>7}{x['form_figure']:>7.1f}{sp:>7}  "
                  f"{tr[:13]+' R'+str(x['race_number'])+' '+str(x['distance_metres'])+'m':<30}{x['finish_position']:>4}")
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "v3_build_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
