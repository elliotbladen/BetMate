#!/usr/bin/env python3
"""
scripts/model_vs_market_football_round.py

Model vs market over a FULL round — EPL GW3 and EFL Championship GW5 —
for both 1X2 and Over/Under 2.5.

Model side
  EPL : outputs/football/epl/2026-27/gw03/1_model.json
        (genuine pre-round prices, saved 2026-09-03)
  EFL : regenerated with scripts/price_efl_week4_2026.py at as_of=2026-09-05.
        price_match filters `Date < as_of`, so there is no lookahead, but it now
        includes the 1-2 Sep midweek round that the 3 Sep originals lacked.

Market side
  football-data.co.uk consensus AVERAGE odds, de-vigged by normalising 1/odds.
    opening = AvgH/AvgD/AvgA, Avg>2.5, Avg<2.5
    closing = AvgCH/AvgCD/AvgCA, AvgC>2.5, AvgC<2.5

Metrics
  1X2 : RPS (the engine's headline metric), multiclass log loss, Brier
  O/U : log loss, Brier
  Lower is better throughout.

Run: python3 scripts/model_vs_market_football_round.py
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs/results"
EPS = 1e-15


def devig(odds: list[float]) -> list[float]:
    raw = [1.0 / o for o in odds]
    s = sum(raw)
    return [r / s for r in raw]


def rps(probs: list[float], outcome: int) -> float:
    """Ranked probability score for ordered 3-outcome H/D/A."""
    obs = [1.0 if i == outcome else 0.0 for i in range(3)]
    cp = cо = 0.0
    total = 0.0
    for i in range(2):
        cp += probs[i]; cо += obs[i]
        total += (cp - cо) ** 2
    return total / 2.0


def logloss(p: float) -> float:
    return -math.log(max(p, EPS))


def brier_multi(probs, outcome):
    return sum((probs[i] - (1.0 if i == outcome else 0.0)) ** 2 for i in range(len(probs)))


def load_epl_model():
    d = json.loads((ROOT / "outputs/football/epl/2026-27/gw03/1_model.json").read_text())
    return {(g["home"], g["away"]): g["normal"] for g in d["games"]}


def load_efl_model():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/price_efl_week4_2026.py")],
                       capture_output=True, text=True, cwd=ROOT)
    out = {}
    for line in r.stdout.splitlines():
        if not line.startswith("RESULT|"):
            continue
        _, h, a, ph, pd_, pa, po, pu = line.split("|")
        out[(h, a)] = {"p_home": float(ph), "p_draw": float(pd_), "p_away": float(pa),
                       "p_over25": float(po), "p_under25": float(pu)}
    return out


def main():
    books = {
        "EPL": pd.read_csv(ROOT / "ml/football/data/epl/matches/epl_matches.csv", low_memory=False),
        "EFL": pd.read_csv(ROOT / "ml/football/data/championship/matches/championship_matches.csv", low_memory=False),
    }
    models = {"EPL": load_epl_model(), "EFL": load_efl_model()}
    windows = {"EPL": ("2026-09-04", "2026-09-06"), "EFL": ("2026-09-05", "2026-09-06")}

    rows = []
    for lg, mdl in models.items():
        df = books[lg]
        lo, hi = windows[lg]
        df = df[(df.Date >= lo) & (df.Date <= hi)]
        for (h, a), m in mdl.items():
            r = df[(df.HomeTeam == h) & (df.AwayTeam == a)]
            if r.empty:
                print(f"  !! no result row for {lg} {h} v {a}")
                continue
            r = r.iloc[0]
            hg, ag = int(r.FTHG), int(r.FTAG)
            outcome = 0 if hg > ag else (1 if hg == ag else 2)
            over = (hg + ag) > 2.5

            mp = [m["p_home"], m["p_draw"], m["p_away"]]
            op = devig([float(r.AvgH), float(r.AvgD), float(r.AvgA)])
            cp = devig([float(r.AvgCH), float(r.AvgCD), float(r.AvgCA)])
            mo = [m["p_over25"], m["p_under25"]]
            oo = devig([float(r["Avg>2.5"]), float(r["Avg<2.5"])])
            co = devig([float(r["AvgC>2.5"]), float(r["AvgC<2.5"])])
            oi = 0 if over else 1

            rows.append(dict(
                league=lg, match=f"{h} v {a}", score=f"{hg}-{ag}",
                result="HDA"[outcome], total_goals=hg + ag, over25=over,
                m_h=round(mp[0], 4), m_d=round(mp[1], 4), m_a=round(mp[2], 4),
                c_h=round(cp[0], 4), c_d=round(cp[1], 4), c_a=round(cp[2], 4),
                m_over=round(mo[0], 4), c_over=round(co[0], 4),
                rps_model=round(rps(mp, outcome), 4), rps_open=round(rps(op, outcome), 4),
                rps_close=round(rps(cp, outcome), 4),
                ll_model=round(logloss(mp[outcome]), 4), ll_close=round(logloss(cp[outcome]), 4),
                br_model=round(brier_multi(mp, outcome), 4), br_close=round(brier_multi(cp, outcome), 4),
                ou_ll_model=round(logloss(mo[oi]), 4), ou_ll_close=round(logloss(co[oi]), 4),
                ou_br_model=round((mo[0] - (1 if over else 0)) ** 2, 4),
                ou_br_close=round((co[0] - (1 if over else 0)) ** 2, 4),
                model_beat_close_1x2=rps(mp, outcome) < rps(cp, outcome),
                model_beat_close_ou=logloss(mo[oi]) < logloss(co[oi]),
            ))

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "epl_efl_model_vs_market_round_2026-09-08.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    def avg(rs, k): return sum(r[k] for r in rs) / len(rs)

    for lg in ("EPL", "EFL"):
        rs = [r for r in rows if r["league"] == lg]
        print(f"\n{'='*104}")
        print(f"{lg} — model vs market, full round ({len(rs)} matches)")
        print(f"{'='*104}")
        print(f"{'Match':<34}{'Score':>7}{'mdl RPS':>9}{'open':>8}{'close':>8}{'winner':>9}"
              f"{'mdl Ovr':>9}{'cls Ovr':>9}{'O/U':>7}")
        for r in rs:
            w1 = "MODEL" if r["model_beat_close_1x2"] else "market"
            w2 = "MODEL" if r["model_beat_close_ou"] else "market"
            print(f"{r['match']:<34}{r['score']:>7}{r['rps_model']:>9.4f}{r['rps_open']:>8.4f}"
                  f"{r['rps_close']:>8.4f}{w1:>9}{r['m_over']:>9.3f}{r['c_over']:>9.3f}{w2:>7}")
        print("-" * 104)
        print(f"  1X2  RPS      model {avg(rs,'rps_model'):.4f} | open {avg(rs,'rps_open'):.4f} | close {avg(rs,'rps_close'):.4f}"
              f"   model beat close {sum(r['model_beat_close_1x2'] for r in rs)}/{len(rs)}")
        print(f"  1X2  log loss model {avg(rs,'ll_model'):.4f} | close {avg(rs,'ll_close'):.4f}")
        print(f"  1X2  Brier    model {avg(rs,'br_model'):.4f} | close {avg(rs,'br_close'):.4f}")
        print(f"  O/U  log loss model {avg(rs,'ou_ll_model'):.4f} | close {avg(rs,'ou_ll_close'):.4f}"
              f"   model beat close {sum(r['model_beat_close_ou'] for r in rs)}/{len(rs)}")
        print(f"  O/U  Brier    model {avg(rs,'ou_br_model'):.4f} | close {avg(rs,'ou_br_close'):.4f}")

    print(f"\n{'='*104}")
    print(f"COMBINED ({len(rows)} matches)")
    print(f"  1X2  RPS      model {avg(rows,'rps_model'):.4f} | open {avg(rows,'rps_open'):.4f} | close {avg(rows,'rps_close'):.4f}"
          f"   model beat close {sum(r['model_beat_close_1x2'] for r in rows)}/{len(rows)}")
    print(f"  1X2  log loss model {avg(rows,'ll_model'):.4f} | close {avg(rows,'ll_close'):.4f}")
    print(f"  O/U  log loss model {avg(rows,'ou_ll_model'):.4f} | close {avg(rows,'ou_ll_close'):.4f}"
          f"   model beat close {sum(r['model_beat_close_ou'] for r in rows)}/{len(rows)}")
    print(f"\nwritten: {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
