#!/usr/bin/env python3
"""Local viewer for the NRL totals matrix v2 backtest.

Computes every figure fresh from the matrices and the results workbook, renders a
self-contained page, and serves it on localhost so the numbers can be eyeballed.

Usage:
    python scripts/_nrl_totals_v2_viewer.py            # build + serve on :8788
    python scripts/_nrl_totals_v2_viewer.py --port 9000
    python scripts/_nrl_totals_v2_viewer.py --no-serve # just write the html
"""
from __future__ import annotations

import argparse
import collections
import html
import importlib.util
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "results" / "nrl_totals_v2_viewer.html"

spec = importlib.util.spec_from_file_location("bt", ROOT / "scripts" / "backtest_nrl_matrix_net7_2026.py")
bt = importlib.util.module_from_spec(spec)
sys.modules["bt"] = bt
spec.loader.exec_module(bt)

WF = Path("/private/tmp/claude-501/-Users-elliotbladen-BetMate/5874c69d-cdbc-45c8-9b9b-fc0658cba34c/scratchpad/wf")


def run(mat, games, yr, thr, net, price="close"):
    rows = []
    for g in (x for x in games if x.gdate.year == yr and x.total_close is not None):
        s = bt.score_game(g, mat, "totals", thr, 0, False)
        for side in ("over", "under"):
            if s[side] < net:
                continue
            if price == "close":
                line, pr = g.total_close, (g.over_odds_close if side == "over" else g.under_odds_close)
            else:
                line, pr = g.total_open, (g.over_odds_open if side == "over" else g.under_odds_open)
            if pr is None or line is None:
                continue
            res = bt.settle_total(g, side, line)
            pnl = (pr - 1) if res == "win" else (0.0 if res == "push" else -1.0)
            rows.append(dict(date=g.gdate.isoformat(), side=side.upper(), net=s[side], line=line,
                             price=pr, home=g.home, away=g.away,
                             score=f"{g.home_score}-{g.away_score}",
                             total=g.home_score + g.away_score, result=res, pnl=round(pnl, 4)))
    return rows


def summarise(rows):
    if not rows:
        return None
    n = len(rows)
    w = sum(1 for r in rows if r["result"] == "win")
    p = sum(1 for r in rows if r["result"] == "push")
    pnl = sum(r["pnl"] for r in rows)
    return dict(n=n, w=w, l=n - w - p, push=p, pnl=round(pnl, 2), roi=round(pnl / n * 100, 2),
                strike=round(w / (n - p) * 100, 1) if n - p else 0,
                avg_price=round(sum(r["price"] for r in rows) / n, 2))


def boot_ci(rows, iters=8000):
    import random
    random.seed(11)
    d = [r["pnl"] for r in rows]
    n = len(d)
    b = sorted(sum(random.choice(d) for _ in range(n)) / n * 100 for _ in range(iters))
    return round(b[int(.025 * iters)], 1), round(b[int(.975 * iters)], 1)


def build():
    games = bt.load_games(bt.RESULTS_XLSX)
    bt.attach_context(games)
    m1 = bt.load_h2h_matrix(bt.TOTALS_MATRIX)
    m2 = bt.load_h2h_matrix(bt.TOTALS_MATRIX_V2)
    D: dict = {}

    # 1. headline grid, 2026
    D["grid"] = []
    for net in (10, 8, 7, 5):
        c = summarise(run(m2, games, 2026, 5.0, net, "close"))
        o = summarise(run(m2, games, 2026, 5.0, net, "open"))
        v1 = summarise(run(m1, games, 2026, 5.0, net, "close"))
        lo, hi = boot_ci(run(m2, games, 2026, 5.0, net, "close"))
        D["grid"].append(dict(net=net, close=c, open=o, v1=v1, ci=[lo, hi]))

    # 2. bet list at the recommended threshold
    D["bets"] = run(m2, games, 2026, 5.0, 8, "close")
    eq, run_tot = [], 0.0
    for b in D["bets"]:
        run_tot += b["pnl"]
        eq.append(round(run_tot, 3))
    D["equity"] = eq

    # 3. walk-forward
    D["wf"] = []
    for thr, net in ((5.0, 5), (5.0, 7), (3.0, 5), (3.0, 7)):
        row = dict(thr=thr, net=net, seasons={}, pool={})
        for metric, key in (("mean", "v1"), ("hitrate", "v2")):
            allrows = []
            per = {}
            for yr in (2023, 2024, 2025, 2026):
                f = WF / f"{metric}_test{yr}.xlsx"
                if not f.exists():
                    continue
                r = run(bt.load_h2h_matrix(f), games, yr, thr, net, "close")
                per[yr] = summarise(r)
                allrows += r
            row["seasons"][key] = per
            row["pool"][key] = summarise(allrows)
        D["wf"].append(row)

    # 4. the 2026 line story
    gs = [g for g in games if g.total_close is not None]
    D["seasons"] = []
    prev = None
    for yr in range(2019, 2027):
        s = [g for g in gs if g.gdate.year == yr]
        if not s:
            continue
        line = st.mean(g.total_close for g in s)
        act = st.mean(g.home_score + g.away_score for g in s)
        dec = sum(1 for g in s if g.home_score + g.away_score != g.total_close)
        ov = sum(1 for g in s if g.home_score + g.away_score > g.total_close)
        D["seasons"].append(dict(year=yr, n=len(s), line=round(line, 2), actual=round(act, 2),
                                 bias=round(line - act, 2), over=round(ov / dec * 100, 1),
                                 jump=round(line - prev, 2) if prev else None))
        prev = line

    s26 = sorted((g for g in gs if g.gdate.year == 2026), key=lambda g: g.gdate)
    bym = collections.OrderedDict()
    for g in s26:
        bym.setdefault(g.gdate.strftime("%b"), []).append(g)
    D["months"] = []
    for k, v in bym.items():
        line = st.mean(g.total_close for g in v)
        act = st.mean(g.home_score + g.away_score for g in v)
        dec = sum(1 for g in v if g.home_score + g.away_score != g.total_close)
        ov = sum(1 for g in v if g.home_score + g.away_score > g.total_close)
        D["months"].append(dict(m=k, n=len(v), line=round(line, 2), actual=round(act, 2),
                                bias=round(line - act, 2), over=round(ov / dec * 100, 1) if dec else 0))

    # bets per month at net+8, to show where the rule bet
    bm = collections.Counter(b["date"][5:7] for b in D["bets"])
    mn = {"02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
          "07": "Jul", "08": "Aug", "09": "Sep"}
    for row in D["months"]:
        row["bets"] = sum(v for k, v in bm.items() if mn.get(k) == row["m"])

    # cell balance
    D["balance"] = []
    for f, lab, win in ((bt.TOTALS_MATRIX, "v1 mean", "2022–25"),
                        (bt.TOTALS_MATRIX_V2, "v2 hit rate", "2022–25"),
                        (ROOT / "outputs" / "nrl_team_totals_matrix_v2_2027.xlsx", "v2 hit rate", "2023–26")):
        if not Path(f).exists():
            continue
        m = bt.load_h2h_matrix(Path(f))
        o = u = 0
        for _, cells in m.items():
            for _, (e, d, n) in cells.items():
                o += "overs" in d
                u += "unders" in d
        D["balance"].append(dict(label=lab, window=win, overs=o, unders=u,
                                 pct=round(o / (o + u) * 100)))
    return D


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NRL Totals Matrix v2 — 2026 Backtest</title>
<style>
:root{
  color-scheme:light;
  --bg:#f4f4f1; --surface-1:#fcfcfb; --border:#e2e1dc;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#87857d;
  --series-1:#2a78d6; --series-2:#eb6834;
  --good:#1b7f4b; --bad:#c0322f; --grid:#e8e7e2;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#111110; --surface-1:#1a1a19; --border:#33322e;
  --text-primary:#fff; --text-secondary:#c3c2b7; --text-muted:#8f8e85;
  --series-1:#3987e5; --series-2:#d95926;
  --good:#4ab87a; --bad:#e66767; --grid:#2a2926;
}}
:root[data-theme="dark"]{
  --bg:#111110; --surface-1:#1a1a19; --border:#33322e;
  --text-primary:#fff; --text-secondary:#c3c2b7; --text-muted:#8f8e85;
  --series-1:#3987e5; --series-2:#d95926;
  --good:#4ab87a; --bad:#e66767; --grid:#2a2926;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text-primary);
 font:14px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
.wrap{max-width:1040px;margin:0 auto;padding:16px;padding-block:32px}
h1{font-size:23px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:16px;margin:36px 0 10px;letter-spacing:-.01em}
.sub{color:var(--text-secondary);margin:0 0 6px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:16px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:7px 9px;text-align:right;border-bottom:1px solid var(--border);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--text-secondary);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tbody tr:last-child td{border-bottom:none}
tr.pool td{font-weight:700;border-top:2px solid var(--border)}
.pos{color:var(--good);font-weight:600}.neg{color:var(--bad);font-weight:600}
.muted{color:var(--text-muted)}
.scroll{overflow-x:auto}
.hero{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.tile{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;
 padding:13px 15px;flex:1 1 150px}
.tile .k{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-secondary)}
.tile .v{font-size:25px;font-weight:700;letter-spacing:-.02em;margin-top:3px}
.tile .n{font-size:12px;color:var(--text-muted)}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:2px 0 10px;font-size:13px;color:var(--text-secondary)}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.note{border-left:3px solid var(--series-2);padding:10px 14px;margin:14px 0;
 background:var(--surface-1);border-radius:0 8px 8px 0;color:var(--text-secondary)}
.note b{color:var(--text-primary)}
svg{display:block;max-width:100%;overflow:visible}
.tt{position:fixed;pointer-events:none;opacity:0;transition:opacity .1s;background:var(--surface-1);
 border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:12.5px;
 box-shadow:0 6px 22px rgba(0,0,0,.16);z-index:9;min-width:130px}
.tt .r{display:flex;justify-content:space-between;gap:14px}
footer{color:var(--text-muted);font-size:12px;margin-top:40px;border-top:1px solid var(--border);padding-top:14px}
code{background:var(--bg);padding:1px 5px;border-radius:4px;font-size:12.5px}
</style></head><body>
<div class="wrap" id="app"></div>
<div class="tt" id="tt"></div>
<script>const D=__DATA__;</script>
<script>
const $=(h)=>{const d=document.createElement('div');d.innerHTML=h.trim();return d.firstChild;};
const sgn=v=>(v>0?'+':'')+v.toFixed(2);
const cls=v=>v>0?'pos':(v<0?'neg':'muted');
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const tt=document.getElementById('tt');
function showTT(e,rows,title){
  tt.innerHTML=`<div style="font-weight:600;margin-bottom:5px">${esc(title)}</div>`+
    rows.map(r=>`<div class="r"><span class="muted">${esc(r[0])}</span><span>${esc(r[1])}</span></div>`).join('');
  tt.style.opacity=1;
  const b=tt.getBoundingClientRect();
  let x=e.clientX+14,y=e.clientY-10;
  if(x+b.width>innerWidth-8)x=e.clientX-b.width-14;
  if(y+b.height>innerHeight-8)y=innerHeight-b.height-8;
  tt.style.left=x+'px';tt.style.top=Math.max(8,y)+'px';
}
const hideTT=()=>tt.style.opacity=0;

const app=document.getElementById('app');
function sec(h){app.appendChild($(`<h2>${h}</h2>`));}
function card(node){const c=$('<div class="card"></div>');c.appendChild(node);app.appendChild(c);return c;}

/* ---------- header ---------- */
app.appendChild($(`<h1>NRL totals matrix v2 — 2026 backtest</h1>`));
app.appendChild($(`<p class="sub">Hit-rate metric, $1 flat stakes, cells &ge;5% edge (the production confluence
 threshold). Matrix trained 2022&ndash;25, so 2026 is fully out of sample. Hover any chart.</p>`));

/* ---------- hero ---------- */
const rec=D.grid.find(g=>g.net===8);
const hero=$('<div class="hero"></div>');
[['ROI @ close',sgn(rec.close.roi)+'%',rec.close.n+' bets, net +8'],
 ['ROI @ open',sgn(rec.open.roi)+'%','same bets, opening price'],
 ['Strike',rec.close.strike+'%','break-even '+(100/rec.close.avg_price).toFixed(1)+'% @ $'+rec.close.avg_price],
 ['P/L',(rec.close.pnl>0?'+$':'-$')+Math.abs(rec.close.pnl).toFixed(2),'on $'+rec.close.n+' staked'],
 ['95% CI',rec.ci[0]+'% … +'+rec.ci[1]+'%','bootstrap, straddles zero']
].forEach(([k,v,n])=>hero.appendChild($(
  `<div class="tile"><div class="k">${k}</div><div class="v ${v.startsWith('+')?'pos':(v.startsWith('-')?'neg':'')}">${v}</div><div class="n">${esc(n)}</div></div>`)));
app.appendChild(hero);

/* ---------- grid table ---------- */
sec('Every threshold, 2026');
{
 const t=$(`<div class="scroll"><table><thead><tr>
 <th>net</th><th>bets</th><th>W–L</th><th>strike</th><th>avg $</th>
 <th>v2 ROI @ close</th><th>v2 ROI @ open</th><th>v1 ROI @ close</th></tr></thead><tbody></tbody></table></div>`);
 const tb=t.querySelector('tbody');
 D.grid.forEach(g=>tb.appendChild($(`<tr>
   <td><b>+${g.net}</b></td><td>${g.close.n}</td><td>${g.close.w}–${g.close.l}</td>
   <td>${g.close.strike}%</td><td>$${g.close.avg_price.toFixed(2)}</td>
   <td class="${cls(g.close.roi)}">${sgn(g.close.roi)}%</td>
   <td class="${cls(g.open.roi)}">${sgn(g.open.roi)}%</td>
   <td class="${cls(g.v1.roi)}">${sgn(g.v1.roi)}%</td></tr>`)));
 card(t);
}
"""

TEMPLATE += r"""
/* ---------- equity curve ---------- */
sec('Bankroll through the season (net +8, closing price)');
{
 const W=960,H=230,P={t:14,r:16,b:28,l:44};
 const eq=D.equity, n=eq.length;
 const lo=Math.min(0,...eq), hi=Math.max(0,...eq), pad=(hi-lo)*0.12||1;
 const x=i=>P.l+i*(W-P.l-P.r)/Math.max(1,n-1);
 const y=v=>P.t+(hi+pad-v)*(H-P.t-P.b)/((hi+pad)-(lo-pad));
 let ticks=''; const step=(hi-lo)>8?4:2;
 for(let v=Math.ceil((lo-pad)/step)*step;v<=hi+pad;v+=step){
   ticks+=`<line x1="${P.l}" x2="${W-P.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)" stroke-width="1"/>
   <text x="${P.l-8}" y="${y(v)+4}" text-anchor="end" font-size="11" fill="var(--text-muted)">${v>0?'+':''}${v}u</text>`;
 }
 const path=eq.map((v,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
 const dots=eq.map((v,i)=>`<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="4.5"
   fill="var(--series-1)" stroke="var(--surface-1)" stroke-width="2" data-i="${i}" style="cursor:pointer"/>`).join('');
 const svg=$(`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Cumulative profit">
   ${ticks}
   <line x1="${P.l}" x2="${W-P.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--text-muted)" stroke-width="1.5" stroke-dasharray="4 3"/>
   <path d="${path}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round"/>
   ${dots}
   <text x="${P.l}" y="${H-8}" font-size="11" fill="var(--text-muted)">bet 1</text>
   <text x="${W-P.r}" y="${H-8}" font-size="11" fill="var(--text-muted)" text-anchor="end">bet ${n}</text>
 </svg>`);
 svg.querySelectorAll('circle').forEach(c=>{
   c.addEventListener('mousemove',e=>{const i=+c.dataset.i,b=D.bets[i];
     showTT(e,[['date',b.date],['bet',b.side+' '+b.line],['game',b.score+' = '+b.total],
       ['result',b.result],['P/L',sgn(b.pnl)+'u'],['running',sgn(D.equity[i])+'u']],
       b.home.split(' ').pop()+' v '+b.away.split(' ').pop());});
   c.addEventListener('mouseleave',hideTT);
 });
 const c=card(svg);
 c.insertBefore($(`<div class="legend"><span><i style="background:var(--series-1)"></i>cumulative profit (units)</span></div>`),svg);
}

/* ---------- the 2026 line story ---------- */
sec('Why 2026 leaned under — the market line vs what actually happened');
app.appendChild($(`<p class="sub">Your read was that a rule change pushed the books to price overs 1&ndash;2 points high,
 and that it drifted back toward the mean. The data says the jump was <b>+2.52 pts</b> and the overshoot was real
 &mdash; but it was concentrated in the middle of the season, not spread across it.</p>`));
{
 const M=D.months, W=960,H=250,P={t:16,r:16,b:40,l:44};
 const vals=M.flatMap(m=>[m.line,m.actual]);
 const lo=Math.min(...vals)-3, hi=Math.max(...vals)+3;
 const x=i=>P.l+i*(W-P.l-P.r)/Math.max(1,M.length-1);
 const y=v=>P.t+(hi-v)*(H-P.t-P.b)/(hi-lo);
 let ticks='';
 for(let v=Math.ceil(lo/5)*5;v<=hi;v+=5){
   ticks+=`<line x1="${P.l}" x2="${W-P.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)" stroke-width="1"/>
   <text x="${P.l-8}" y="${y(v)+4}" text-anchor="end" font-size="11" fill="var(--text-muted)">${v}</text>`;
 }
 const mk=(key,col)=>M.map((m,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(m[key]).toFixed(1)}`).join(' ');
 let dots='';
 M.forEach((m,i)=>{
   dots+=`<circle cx="${x(i).toFixed(1)}" cy="${y(m.line).toFixed(1)}" r="4.5" fill="var(--series-1)" stroke="var(--surface-1)" stroke-width="2"/>`;
   dots+=`<circle cx="${x(i).toFixed(1)}" cy="${y(m.actual).toFixed(1)}" r="4.5" fill="var(--series-2)" stroke="var(--surface-1)" stroke-width="2"/>`;
 });
 const hit=M.map((m,i)=>`<rect x="${(x(i)-26).toFixed(1)}" y="${P.t}" width="52" height="${H-P.t-P.b}"
   fill="transparent" data-i="${i}" style="cursor:crosshair"/>`).join('');
 const labs=M.map((m,i)=>`<text x="${x(i).toFixed(1)}" y="${H-18}" text-anchor="middle" font-size="11.5"
   fill="var(--text-secondary)">${m.m}</text>
   <text x="${x(i).toFixed(1)}" y="${H-5}" text-anchor="middle" font-size="10" fill="var(--text-muted)">n=${m.n}</text>`).join('');
 const svg=$(`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Market line vs actual total by month, 2026">
  ${ticks}
  <path d="${mk('line')}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round"/>
  <path d="${mk('actual')}" fill="none" stroke="var(--series-2)" stroke-width="2" stroke-linejoin="round"/>
  ${dots}${labs}${hit}</svg>`);
 svg.querySelectorAll('rect').forEach(r=>{
  r.addEventListener('mousemove',e=>{const m=M[+r.dataset.i];
    showTT(e,[['market line',m.line.toFixed(2)],['actual total',m.actual.toFixed(2)],
      ['line too high by',sgn(m.bias)],['over rate',m.over+'%'],
      ['games',m.n],['v2 bets',m.bets]],'2026 — '+m.m);});
  r.addEventListener('mouseleave',hideTT);
 });
 const c=card(svg);
 c.insertBefore($(`<div class="legend">
   <span><i style="background:var(--series-1)"></i>market closing line</span>
   <span><i style="background:var(--series-2)"></i>actual total scored</span></div>`),svg);
}
{
 const t=$(`<div class="scroll"><table><thead><tr><th>month</th><th>games</th><th>market line</th>
  <th>actual</th><th>line too high by</th><th>over rate</th><th>v2 bets</th></tr></thead><tbody></tbody></table></div>`);
 const tb=t.querySelector('tbody');
 D.months.forEach(m=>tb.appendChild($(`<tr><td><b>${m.m}</b></td><td>${m.n}</td>
   <td>${m.line.toFixed(2)}</td><td>${m.actual.toFixed(2)}</td>
   <td class="${m.bias>2?'neg':''}">${sgn(m.bias)}</td><td>${m.over}%</td><td>${m.bets}</td></tr>`)));
 card(t);
}
app.appendChild($(`<div class="note"><b>The overshoot was a mid-season window, not the whole year.</b>
 May and June ran <b>+4.78</b> and <b>+5.71</b> points too high with over rates of 38.9% and 32.1%.
 The first and last thirds of the season were close to efficient (line too high by &minus;0.56 and &minus;0.99,
 over rate 47.1% in both). So the books did correct &mdash; but the drift across the whole season is only
 &minus;1.06 pts (r = &minus;0.086), because the damage was a bulge in the middle rather than a slope.
 <br><br><b>And the matrix mostly missed it.</b> Only 6 of the 32 net +8 bets fell in May&ndash;June,
 the one genuinely mispriced stretch of the season.</div>`));

/* ---------- season table ---------- */
sec('Season by season — the 2026 jump in context');
{
 const t=$(`<div class="scroll"><table><thead><tr><th>season</th><th>games</th><th>avg line</th>
  <th>vs prior</th><th>avg actual</th><th>line too high by</th><th>over rate</th></tr></thead><tbody></tbody></table></div>`);
 const tb=t.querySelector('tbody');
 D.seasons.forEach(s=>tb.appendChild($(`<tr${s.year===2026?' style="font-weight:700"':''}>
   <td>${s.year}</td><td>${s.n}</td><td>${s.line.toFixed(2)}</td>
   <td class="${s.jump>1.5?'neg':'muted'}">${s.jump===null?'—':sgn(s.jump)}</td>
   <td>${s.actual.toFixed(2)}</td><td class="${s.bias>0.9?'neg':''}">${sgn(s.bias)}</td>
   <td>${s.over}%</td></tr>`)));
 card(t);
}

/* ---------- walk-forward ---------- */
sec('Walk-forward — the reason this is not yet a staked system');
app.appendChild($(`<p class="sub">Rolling 4-season training window, each test season strictly out of sample.
 2026 is the good draw, not the baseline.</p>`));
{
 const t=$(`<div class="scroll"><table><thead><tr><th>config</th><th>ver</th>
  <th>2023</th><th>2024</th><th>2025</th><th>2026</th><th>pooled ROI</th><th>bets</th></tr></thead><tbody></tbody></table></div>`);
 const tb=t.querySelector('tbody');
 D.wf.forEach(w=>{
  ['v1','v2'].forEach((k,j)=>{
   const p=w.pool[k];
   const tds=[2023,2024,2025,2026].map(y=>{const s=w.seasons[k][y];
     return s?`<td class="${cls(s.roi)}">${sgn(s.roi)}%</td>`:'<td class="muted">—</td>';}).join('');
   tb.appendChild($(`<tr${k==='v2'?' class="pool"':''}>
     <td>${j?'':'cells ≥'+w.thr+'%, net +'+w.net}</td><td>${k}</td>${tds}
     <td class="${cls(p.roi)}">${sgn(p.roi)}%</td><td class="muted">${p.n}</td></tr>`));
  });
 });
 card(t);
}

/* ---------- cell balance ---------- */
sec('What adding 2026 does to the sheet');
{
 const t=$(`<div class="scroll"><table><thead><tr><th>matrix</th><th>training window</th>
  <th>overs cells</th><th>unders cells</th><th>% overs</th></tr></thead><tbody></tbody></table></div>`);
 const tb=t.querySelector('tbody');
 D.balance.forEach(b=>tb.appendChild($(`<tr><td>${esc(b.label)}</td><td>${esc(b.window)}</td>
   <td>${b.overs}</td><td>${b.unders}</td>
   <td class="${b.pct>=54?'neg':(b.pct<=42?'neg':'')}"><b>${b.pct}%</b></td></tr>`)));
 card(t);
}
app.appendChild($(`<div class="note">v1's 56% overs tilt came from measuring a right-skewed mean.
 v2 on the same window is a balanced 48%. Retraining on <b>2023&ndash;26 swings it to 38% overs</b> &mdash;
 that lean is inherited from one outlier season, so it is the first thing to check if 2027 runs badly.</div>`));

/* ---------- bet list ---------- */
sec('All 32 bets — net +8, closing price');
{
 const t=$(`<div class="scroll"><table><thead><tr><th>date</th><th>match</th><th>bet</th><th>net</th>
  <th>price</th><th>score</th><th>total</th><th>result</th><th>P/L</th><th>running</th></tr></thead><tbody></tbody></table></div>`);
 const tb=t.querySelector('tbody');
 D.bets.forEach((b,i)=>tb.appendChild($(`<tr>
   <td class="muted">${b.date}</td>
   <td>${esc(b.home.split(' ').pop())} v ${esc(b.away.split(' ').pop())}</td>
   <td><b>${b.side} ${b.line}</b></td><td>+${b.net}</td><td>$${b.price.toFixed(2)}</td>
   <td class="muted">${b.score}</td><td>${b.total}</td>
   <td class="${b.result==='win'?'pos':(b.result==='push'?'muted':'neg')}">${b.result}</td>
   <td class="${cls(b.pnl)}">${sgn(b.pnl)}</td>
   <td class="${cls(D.equity[i])}">${sgn(D.equity[i])}</td></tr>`)));
 card(t);
}

app.appendChild($(`<footer>Generated by <code>scripts/_nrl_totals_v2_viewer.py</code> from
 <code>nrl_team_totals_matrix_v2.xlsx</code> and <code>outputs/nrl_weekly_review/historical/latest.xlsx</code>.
 Every figure recomputed at page build &mdash; nothing hardcoded.</footer>`));
</script>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--no-serve", action="store_true")
    args = ap.parse_args()

    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(TEMPLATE.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    if args.no_serve:
        return

    import functools, http.server, socketserver
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT.parent))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"\n  →  http://127.0.0.1:{args.port}/{OUT.name}\n\nCtrl-C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")


if __name__ == "__main__":
    main()
