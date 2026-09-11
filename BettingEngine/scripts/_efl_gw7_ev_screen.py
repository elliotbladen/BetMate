#!/usr/bin/env python3
"""EV screen for Championship GW7 — 1X2 and O/U 2.5, normal and shadow,
priced with and without T5 so an edge that only exists because of an injury
input is visible as such."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GW = ROOT / "outputs" / "football" / "championship" / "2026-27" / "gw07"

on = {(g["home"], g["away"]): g for g in json.loads((GW / "1_model.json").read_text())["games"]}
off = {(g["home"], g["away"]): g for g in
       json.loads((GW / "_supporting" / "model_t5_off.json").read_text())["games"]}

SEL = [("home", "avg_home", "best_home", "p_home"),
       ("draw", "avg_draw", "best_draw", "p_draw"),
       ("away", "avg_away", "best_away", "p_away"),
       ("over25", "avg_over25", "best_over25", "p_over25"),
       ("under25", "avg_under25", "best_under25", "p_under25")]

rows = []
for key, g in on.items():
    m, nv = g["market"], g["market_novig"]
    for name, avgc, bestc, pk in SEL:
        p_on = g["normal"][pk]
        p_off = off[key]["normal"][pk]
        p_sh = g["shadow"][pk]
        rows.append({
            "date": g["date"], "match": f"{g['home']} v {g['away']}", "selection": name,
            "market_avg": m[avgc], "market_best": m[bestc], "best_book": m[f"{bestc}_book"],
            "market_novig_p": round(nv[name], 4),
            "p_normal_t5on": round(p_on, 4), "p_normal_t5off": round(p_off, 4),
            "p_shadow": round(p_sh, 4),
            "ev_best_t5on": round(p_on * m[bestc] - 1, 4),
            "ev_best_t5off": round(p_off * m[bestc] - 1, 4),
            "ev_best_shadow": round(p_sh * m[bestc] - 1, 4),
            "ev_avg_t5on": round(p_on * m[avgc] - 1, 4),
            "edge_vs_novig": round(p_on - nv[name], 4),
            "dc_reset": ", ".join(g["dc_reset_teams"]),
            "market": "1X2" if name in ("home", "draw", "away") else "OU25",
        })

df = pd.DataFrame(rows)
df.to_csv(GW / "_supporting" / "ev_screen.csv", index=False)

pd.set_option("display.width", 250)
for mk in ("1X2", "OU25"):
    d = df[df.market.eq(mk)].sort_values("ev_best_t5on", ascending=False)
    print(f"\n{'='*118}\n{mk} — ranked by EV at best price (T5 on)\n{'='*118}")
    print(f"{'match':<30}{'sel':<8}{'best':>6}{'avg':>7}{'novig':>7}{'p_on':>7}{'p_off':>7}{'p_sh':>7}"
          f"{'EVbest':>8}{'EVoff':>8}{'EVsh':>8}  reset")
    for _, r in d.head(14).iterrows():
        print(f"{r['match']:<30}{r.selection:<8}{r.market_best:>6.2f}{r.market_avg:>7.2f}"
              f"{r.market_novig_p:>7.3f}{r.p_normal_t5on:>7.3f}{r.p_normal_t5off:>7.3f}{r.p_shadow:>7.3f}"
              f"{r.ev_best_t5on:>+8.1%}{r.ev_best_t5off:>+8.1%}{r.ev_best_shadow:>+8.1%}  {r.dc_reset}")

print(f"\n\nQualifiers at >=10% EV on best price (T5 on): {int((df.ev_best_t5on>=0.10).sum())}")
print(f"  ... of which also >=10% with T5 off      : "
      f"{int(((df.ev_best_t5on>=0.10)&(df.ev_best_t5off>=0.10)).sum())}")
print(f"  ... and also >=10% on the shadow          : "
      f"{int(((df.ev_best_t5on>=0.10)&(df.ev_best_t5off>=0.10)&(df.ev_best_shadow>=0.10)).sum())}")
print(f"  ... and free of a D-C-reset club          : "
      f"{int(((df.ev_best_t5on>=0.10)&(df.ev_best_t5off>=0.10)&(df.ev_best_shadow>=0.10)&(df.dc_reset.eq(''))).sum())}")

print("\n--- totals model resolution ---")
o = df[df.selection.eq('over25')]
print(f"distinct model P(Over) across the 12 fixtures: {sorted(o.p_normal_t5on.unique())}")
print(f"model mean P(Over) {o.p_normal_t5on.mean():.3f}  vs  market no-vig mean {o.market_novig_p.mean():.3f}")
print(f"model below market in {int((o.p_normal_t5on < o.market_novig_p).sum())}/12 fixtures")
