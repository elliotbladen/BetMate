#!/usr/bin/env python3
"""
scripts/player_shadow_round_review.py

Player-shadow review for a completed round: SHADOW vs NORMAL vs MARKET,
on both accuracy (RPS / log loss / Brier) and betting (ROI / CLV).

Model prices come from the round's `1_model.json`, which carries a `normal` and
a `shadow` block per game. Market comes from football-data consensus averages,
de-vigged. Notional bet = each model's best-EV side at the OPENING price, held
to the close, so ROI and CLV are like-for-like between the two engines.

Writes into the round folder, per the records convention:
    outputs/football/{comp}/{season}/{gwNN}/3_review_shadow.{csv,md}

Run: python3 scripts/player_shadow_round_review.py
"""
from __future__ import annotations

import csv, json, math
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EPS = 1e-15

ROUNDS = [
    # comp key, label, round dir, matches csv, result window
    ("epl", "EPL GW3", "outputs/football/epl/2026-27/gw03",
     "ml/football/data/epl/matches/epl_matches.csv", ("2026-09-04", "2026-09-06")),
]


def devig(o): 
    r = [1/x for x in o]; s = sum(r); return [x/s for x in r]

def rps(p, o):
    obs = [1.0 if i == o else 0.0 for i in range(3)]
    cp = co = t = 0.0
    for i in range(2):
        cp += p[i]; co += obs[i]; t += (cp-co)**2
    return t/2

def ll(p): return -math.log(max(p, EPS))
def brier(p, o): return sum((p[i]-(1.0 if i==o else 0.0))**2 for i in range(len(p)))


def review(key, label, rdir, mcsv, window):
    d = json.loads((ROOT/rdir/"1_model.json").read_text())
    df = pd.read_csv(ROOT/mcsv, low_memory=False)
    df = df[(df.Date >= window[0]) & (df.Date <= window[1])]

    rows = []
    for g in d["games"]:
        h, a = g["home"], g["away"]
        m = df[(df.HomeTeam == h) & (df.AwayTeam == a)]
        if m.empty or not g.get("shadow"):
            continue
        r = m.iloc[0]
        hg, ag = int(r.FTHG), int(r.FTAG)
        oc = 0 if hg > ag else (1 if hg == ag else 2)
        over = (hg+ag) > 2.5
        oi = 0 if over else 1

        opens  = [float(r.AvgH), float(r.AvgD), float(r.AvgA)]
        closes = [float(r.AvgCH), float(r.AvgCD), float(r.AvgCA)]
        oo = [float(r["Avg>2.5"]), float(r["Avg<2.5"])]
        co = [float(r["AvgC>2.5"]), float(r["AvgC<2.5"])]
        mkt_c = devig(closes); mkt_co = devig(co)

        rec = dict(match=f"{h} v {a}", score=f"{hg}-{ag}", result="HDA"[oc], over25=over)
        for tag, blk in (("normal", g["normal"]), ("shadow", g["shadow"])):
            p3 = [blk["p_home"], blk["p_draw"], blk["p_away"]]
            p2 = [blk["p_over25"], blk["p_under25"]]
            ev3 = [p*o-1 for p, o in zip(p3, opens)]; i3 = ev3.index(max(ev3))
            ev2 = [p*o-1 for p, o in zip(p2, oo)];    i2 = ev2.index(max(ev2))
            w3 = (i3 == oc); w2 = (i2 == oi)
            rec |= {
                f"{tag}_rps": round(rps(p3, oc), 4),
                f"{tag}_ll": round(ll(p3[oc]), 4),
                f"{tag}_brier": round(brier(p3, oc), 4),
                f"{tag}_ou_ll": round(ll(p2[oi]), 4),
                f"{tag}_1x2_pick": "HDA"[i3],
                f"{tag}_1x2_clv": round((opens[i3]/closes[i3]-1)*100, 2),
                f"{tag}_1x2_pnl": round(opens[i3]-1 if w3 else -1.0, 3),
                f"{tag}_ou_pick": "OVER" if i2 == 0 else "UNDER",
                f"{tag}_ou_clv": round((oo[i2]/co[i2]-1)*100, 2),
                f"{tag}_ou_pnl": round(oo[i2]-1 if w2 else -1.0, 3),
            }
        rec |= {"market_rps": round(rps(mkt_c, oc), 4), "market_ll": round(ll(mkt_c[oc]), 4),
                "market_brier": round(brier(mkt_c, oc), 4), "market_ou_ll": round(ll(mkt_co[oi]), 4)}
        rows.append(rec)

    if not rows:
        print(f"  {label}: no rows"); return None

    out = ROOT/rdir/"3_review_shadow.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    def av(k): return sum(r[k] for r in rows)/len(rows)
    def tot(k): return sum(r[k] for r in rows)
    n = len(rows)

    print(f"\n{'='*92}\n{label} — player shadow vs normal vs market ({n} matches)\n{'='*92}")
    print(f"{'Metric':<22}{'SHADOW':>12}{'NORMAL':>12}{'MARKET':>12}   winner")
    for lbl, sk, nk, mk in (("1X2 RPS","shadow_rps","normal_rps","market_rps"),
                            ("1X2 log loss","shadow_ll","normal_ll","market_ll"),
                            ("1X2 Brier","shadow_brier","normal_brier","market_brier"),
                            ("O/U log loss","shadow_ou_ll","normal_ou_ll","market_ou_ll")):
        vals = {"shadow": av(sk), "normal": av(nk), "market": av(mk)}
        best = min(vals, key=vals.get)
        print(f"{lbl:<22}{vals['shadow']:>12.4f}{vals['normal']:>12.4f}{vals['market']:>12.4f}   {best.upper()}")

    print(f"\n{'Betting (1u per pick, best-EV side at the open)':<48}{'SHADOW':>12}{'NORMAL':>12}")
    for lbl, sk, nk in (("1X2 P&L (u)","shadow_1x2_pnl","normal_1x2_pnl"),
                        ("O/U P&L (u)","shadow_ou_pnl","normal_ou_pnl")):
        print(f"{lbl:<48}{tot(sk):>+12.2f}{tot(nk):>+12.2f}")
    for lbl, sk, nk in (("1X2 ROI %","shadow_1x2_pnl","normal_1x2_pnl"),
                        ("O/U ROI %","shadow_ou_pnl","normal_ou_pnl")):
        print(f"{lbl:<48}{tot(sk)/n*100:>+12.2f}{tot(nk)/n*100:>+12.2f}")
    for lbl, sk, nk in (("1X2 avg CLV %","shadow_1x2_clv","normal_1x2_clv"),
                        ("O/U avg CLV %","shadow_ou_clv","normal_ou_clv")):
        print(f"{lbl:<48}{av(sk):>+12.2f}{av(nk):>+12.2f}")
    diff = sum(1 for r in rows if r["shadow_1x2_pick"] != r["normal_1x2_pick"])
    diff2 = sum(1 for r in rows if r["shadow_ou_pick"] != r["normal_ou_pick"])
    print(f"\nPicks where shadow differed from normal: 1X2 {diff}/{n}, O/U {diff2}/{n}")
    print(f"written: {out.relative_to(ROOT)}")
    return rows, out


def main():
    for args in ROUNDS:
        review(*args)


if __name__ == "__main__":
    main()
