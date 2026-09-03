#!/usr/bin/env python3
"""Calibrated NRL margin/total Monte Carlo layered on a pricing CSV."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def calibration_errors():
    pairs = []
    folder = ROOT / "data" / "model_accuracy" / "nrl"
    for path in sorted(folder.glob("NRL_MODEL_ACCURACY_R*_2026-*.csv")):
        games = {}
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                key = (row["date"], row["home_team"], row["away_team"])
                games.setdefault(key, {})[row["market"]] = row
        for markets in games.values():
            if "handicap" not in markets or "total" not in markets:
                continue
            h, t = markets["handicap"], markets["total"]
            try:
                pairs.append((float(h["actual"]) - float(h["rules_model"]),
                              float(t["actual"]) - float(t["rules_model"])))
            except (TypeError, ValueError):
                pass
    if len(pairs) < 16:
        raise RuntimeError(f"Only {len(pairs)} paired calibration games; need at least 16")
    arr = np.asarray(pairs, dtype=float)
    # Center errors: the rules price remains the expected value. Bias correction
    # belongs in model calibration, not in the uncertainty layer.
    return arr - arr.mean(axis=0), arr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pricing_csv")
    ap.add_argument("--simulations", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=27092026)
    ap.add_argument("--output-dir", default="outputs/monte_carlo/nrl")
    args = ap.parse_args()

    centered, raw = calibration_errors()
    cov = np.cov(centered.T, ddof=1)
    rng = np.random.default_rng(args.seed)
    with open(args.pricing_csv, encoding="utf-8-sig", newline="") as fh:
        prices = list(csv.DictReader(fh))

    output = []
    for row in prices:
        margin, total = float(row["final_margin"]), float(row["final_total"])
        # Heavy team rotation makes the mean less certain. Inflate both error
        # dimensions for a full +/-3 point availability clamp.
        rotation = abs(float(row.get("t5_hcap") or 0.0)) >= 3.0
        local_cov = cov * (1.15 ** 2 if rotation else 1.0)
        errors = rng.multivariate_normal([0.0, 0.0], local_cov, size=args.simulations)
        raw_margin = margin + errors[:, 0]
        raw_total = total + errors[:, 1]
        # Convert the sampled margin/total pair to feasible team scores. Normal
        # residual tails can otherwise imply negative points in mismatches.
        home_pts = np.maximum(0.0, (raw_total + raw_margin) / 2.0)
        away_pts = np.maximum(0.0, (raw_total - raw_margin) / 2.0)
        sim_margin = home_pts - away_pts
        sim_total = home_pts + away_pts
        # Half of exact ties are allocated to either side, matching golden-point
        # resolution without pretending the regular-time tie is a third market.
        p_home = float(np.mean(sim_margin > 0) + 0.5 * np.mean(sim_margin == 0))
        p_away = 1.0 - p_home
        rec = {
            "season": int(row["season"]), "round": 27,
            "home": row["home"], "away": row["away"],
            "model_margin": round(margin, 2), "model_total": round(total, 2),
            "simulations": args.simulations, "seed": args.seed,
            "calibration_games": len(raw),
            "margin_error_sd": round(float(np.sqrt(local_cov[0, 0])), 3),
            "total_error_sd": round(float(np.sqrt(local_cov[1, 1])), 3),
            "error_correlation": round(float(local_cov[0, 1] /
                                               np.sqrt(local_cov[0, 0] * local_cov[1, 1])), 3),
            "rotation_uncertainty": rotation,
            "home_win_probability": round(p_home, 4),
            "away_win_probability": round(p_away, 4),
            "mc_fair_home_odds": round(1 / p_home, 3),
            "mc_fair_away_odds": round(1 / p_away, 3),
            "margin_p10": round(float(np.quantile(sim_margin, .10)), 1),
            "margin_p50": round(float(np.quantile(sim_margin, .50)), 1),
            "margin_p90": round(float(np.quantile(sim_margin, .90)), 1),
            "total_p10": round(float(np.quantile(sim_total, .10)), 1),
            "total_p50": round(float(np.quantile(sim_total, .50)), 1),
            "total_p90": round(float(np.quantile(sim_total, .90)), 1),
            "home_score_p20": round(float(np.quantile(home_pts, .20)), 0),
            "home_score_p80": round(float(np.quantile(home_pts, .80)), 0),
            "away_score_p20": round(float(np.quantile(away_pts, .20)), 0),
            "away_score_p80": round(float(np.quantile(away_pts, .80)), 0),
        }
        output.append(rec)

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "nrl_r27_2026_simulations"
    csv_path, json_path = out_dir / f"{stem}.csv", out_dir / f"{stem}.json"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=output[0].keys())
        writer.writeheader(); writer.writerows(output)
    json_path.write_text(json.dumps({
        "method": "bivariate-normal centered historical rules residuals",
        "raw_error_bias": {"margin": round(float(raw[:, 0].mean()), 3),
                           "total": round(float(raw[:, 1].mean()), 3)},
        "games": output,
    }, indent=2), encoding="utf-8")
    for r in output:
        print(f"{r['home']} v {r['away']}: {r['home_win_probability']:.1%}/"
              f"{r['away_win_probability']:.1%}, MC fair "
              f"{r['mc_fair_home_odds']:.2f}/{r['mc_fair_away_odds']:.2f}")
    print(f"Wrote {csv_path}\nWrote {json_path}")


if __name__ == "__main__":
    main()
