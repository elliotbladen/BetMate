"""Monte Carlo for NRL finals week 2.

Dispersion is NOT assumed — margin SD 18.88 and totals SD 13.53 were measured this
session from 2024-26 AusSportsBetting closing lines vs actual results (n=273 / 634),
and cross-checked against the documented model RMSE of 18.39.

Two runs per game:
  frozen      — the engine's price as built
  market-blend— 50/50 model/market, the sensitivity that matters because the model's
                2026 margin MAE (14.49) is WORSE than the market's (14.28), so a large
                model-vs-market gap should be read as the model being wrong.
"""
import numpy as np
N=200_000; SD_M, SD_T = 18.88, 13.53
rng=np.random.default_rng(42)

GAMES=[
 dict(name="SF1  Roosters v Sharks  (Allianz, Sat 19 Sep)",
      home="Roosters", away="Sharks",
      model_margin=1.4, model_total=47.0,
      mkt_line=6.5, mkt_line_price=1.90,      # home -6.5
      mkt_home=1.44, mkt_away=2.82,
      mkt_total=45.5, mkt_over=1.90, mkt_under=1.90),
 dict(name="SF2  Warriors v Knights (Eden Park, Sun 20 Sep)",
      home="Warriors", away="Knights",
      model_margin=9.3, model_total=51.5,
      mkt_line=5.5, mkt_line_price=1.90,
      mkt_home=1.51, mkt_away=2.57,
      mkt_total=44.5, mkt_over=1.90, mkt_under=1.90),
]
def ev(p,price): return p*price-1
for g in GAMES:
    mkt_margin = g['mkt_line']                       # market's expected home margin
    for label, mm, mt in (("frozen", g['model_margin'], g['model_total']),
                          ("50/50 blend", (g['model_margin']+mkt_margin)/2,
                                          (g['model_total']+g['mkt_total'])/2)):
        m=rng.normal(mm,SD_M,N); t=rng.normal(mt,SD_T,N)
        p_home=(m>0).mean()
        p_cover_home=(m-g['mkt_line']>0).mean()      # home -line
        p_cover_away=1-p_cover_home
        p_over=(t>g['mkt_total']).mean()
        print(f"\n{g['name']}   [{label}]  model margin {mm:+.1f}  total {mt:.1f}")
        print(f"   H2H  {g['home']} {p_home*100:5.1f}%  fair ${1/p_home:5.2f}  mkt ${g['mkt_home']:.2f}  EV {ev(p_home,g['mkt_home'])*100:+6.1f}%")
        print(f"        {g['away']} {(1-p_home)*100:5.1f}%  fair ${1/(1-p_home):5.2f}  mkt ${g['mkt_away']:.2f}  EV {ev(1-p_home,g['mkt_away'])*100:+6.1f}%")
        print(f"   LINE {g['home']} -{g['mkt_line']}  {p_cover_home*100:5.1f}%  EV {ev(p_cover_home,g['mkt_line_price'])*100:+6.1f}%"
              f"   |  {g['away']} +{g['mkt_line']}  {p_cover_away*100:5.1f}%  EV {ev(p_cover_away,g['mkt_line_price'])*100:+6.1f}%")
        print(f"   TOTAL {g['mkt_total']}  Over {p_over*100:5.1f}% EV {ev(p_over,g['mkt_over'])*100:+6.1f}%"
              f"   |  Under {(1-p_over)*100:5.1f}% EV {ev(1-p_over,g['mkt_under'])*100:+6.1f}%")
