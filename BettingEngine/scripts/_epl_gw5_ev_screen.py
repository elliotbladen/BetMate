import json
from pathlib import Path
SUP=Path('outputs/football/epl/2026-27/gw05/_supporting')
d=json.load(open(SUP/'gw05_prices.json'))
MKT={  # best available, Odds API uk region, 2026-09-15
 ('Brentford','Chelsea'):        dict(H=3.05,D=4.00,A=2.32,O=1.44,U=2.50),
 ('Tottenham','Aston Villa'):    dict(H=2.08,D=3.75,A=3.90,O=1.82,U=2.10),
 ('Brighton','Arsenal'):         dict(H=5.20,D=4.10,A=1.75,O=1.81,U=2.12),
 ('Everton','Ipswich'):          dict(H=1.83,D=4.00,A=4.80,O=1.80,U=2.18),
 ('Newcastle','Hull'):           dict(H=1.66,D=4.50,A=5.60,O=1.68,U=2.30),
 ("Nott'm Forest",'Coventry'):   dict(H=1.70,D=4.10,A=5.60,O=1.83,U=2.08),
 ('Bournemouth','Liverpool'):    dict(H=3.25,D=3.95,A=2.22,O=1.44,U=2.62),
 ('Leeds','Crystal Palace'):     dict(H=1.85,D=3.95,A=4.70,O=1.82,U=2.16),
 ('Man City','Sunderland'):      dict(H=1.34,D=6.00,A=11.0,O=1.62,U=2.46),
 ('Fulham','Man United'):        dict(H=3.65,D=3.95,A=2.08,O=1.57,U=2.30),
}
PROMOTED={'Coventry','Hull','Ipswich'}
rows=[]
for g in d['games']:
    m=MKT[(g['home'],g['away'])]; p=g['price']
    novig_h = (1/m['H'])/((1/m['H'])+(1/m['D'])+(1/m['A']))
    novig_o = (1/m['O'])/((1/m['O'])+(1/m['U']))
    rows.append(dict(h=g['home'],a=g['away'],date=g['date'],
        ph=p['p_home'],pd=p['p_draw'],pa=p['p_away'],po=p['p_over25'],
        mH=m['H'],mD=m['D'],mA=m['A'],mO=m['O'],mU=m['U'],
        evH=p['p_home']*m['H']-1, evD=p['p_draw']*m['D']-1, evA=p['p_away']*m['A']-1,
        evO=p['p_over25']*m['O']-1, evU=(1-p['p_over25'])*m['U']-1,
        nvh=novig_h, nvo=novig_o,
        lam=p['lambda_home'], mu=p['lambda_away'],
        flag=('PROMOTED' if (g['home'] in PROMOTED or g['away'] in PROMOTED) else '')))
json.dump(rows,open(SUP/'gw05_ev.json','w'),indent=1)
print(f"{'fixture':34s} {'model H/D/A':>22s} {'EV H':>7s} {'EV D':>7s} {'EV A':>7s} | {'mdl O':>6s} {'mkt O':>6s} {'EV O':>7s} {'EV U':>7s}  flag")
for r in rows:
    print(f"{r['h']+' v '+r['a']:34s} {r['ph']*100:6.1f}%{r['pd']*100:6.1f}%{r['pa']*100:6.1f}% "
          f"{r['evH']*100:+6.1f}% {r['evD']*100:+6.1f}% {r['evA']*100:+6.1f}% | "
          f"{r['po']*100:5.1f}% {r['nvo']*100:5.1f}% {r['evO']*100:+6.1f}% {r['evU']*100:+6.1f}%  {r['flag']}")
print()
mo=sum(r['po'] for r in rows)/len(rows); mk=sum(r['nvo'] for r in rows)/len(rows)
print(f"  model mean P(Over2.5) {mo*100:.1f}%  vs de-vigged market {mk*100:.1f}%  -> model is {(mo-mk)*100:+.1f}pp HIGH")
print(f"  distinct model P(Over) values across 10 fixtures: {len(set(round(r['po'],4) for r in rows))}")
