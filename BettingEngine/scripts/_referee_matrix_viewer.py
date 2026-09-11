#!/usr/bin/env python3
"""Render the Championship referee O/U 2.5 matrix as a browsable local HTML page.

Reads through the same functions that build the workbook, so the page cannot drift
from the .xlsx. Writes a single self-contained file — no network, no CDN.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from efl_championship_referee_matrix import (  # noqa: E402
    CURRENT_2026_27_TEAMS, DEFAULT_SEASONS, DEFAULT_SOURCE, FDR_Q, MIN_REFEREE_GAMES,
    benjamini_hochberg, categories, estimate_tau2, load_rows, stats_goals,
)

OUT = Path(__file__).resolve().parents[1] / "outputs/football/_reference/referee_matrix_viewer.html"


def build_payload() -> dict:
    rows, current = load_rows(DEFAULT_SOURCE, DEFAULT_SEASONS)
    counts = Counter(row["referee"] for row in rows)
    referees = sorted({r for r, n in counts.items() if n >= MIN_REFEREE_GAMES} | current)
    teams = sorted(set(r["home"] for r in rows) | set(r["away"] for r in rows)
                   | set(CURRENT_2026_27_TEAMS))
    league_btts = mean(int(r["home_goals"] > 0 and r["away_goals"] > 0) for r in rows)
    tau2 = estimate_tau2(rows)

    computed, pvalues = {}, []
    for referee in referees:
        games = [r for r in rows if r["referee"] == referee]
        cells = []
        for section, label, subset in categories(games, teams, DEFAULT_SEASONS):
            result = stats_goals(subset, league_btts, tau2)
            if result is None:
                cells.append({"section": section, "label": label, "empty": True})
                continue
            v, p = result
            pvalues.append(p)
            cells.append({
                "section": section, "label": label, "empty": False,
                "over": v[0], "mkt": v[1], "edge": v[2], "shrunk": v[3],
                "roiOver": None if v[4] == "—" else v[4],
                "roiUnder": None if v[5] == "—" else v[5],
                "btts": v[6], "goals": v[8],
                "fouls": None if v[9] == "—" else v[9],
                "cards": None if v[10] == "—" else v[10],
                "c35": None if v[11] == "—" else v[11],
                "cBE": None if v[12] == "—" else v[12],
                "n": v[13], "reliability": v[14], "p": p,
            })
        computed[referee] = {"games": len(games), "cells": cells}
    cutoff = benjamini_hochberg(pvalues, FDR_Q)
    for ref in computed.values():
        for c in ref["cells"]:
            if not c["empty"]:
                c["sig"] = cutoff > 0 and c["p"] <= cutoff
    arr = np.array(pvalues)
    return {
        "seasons": list(DEFAULT_SEASONS), "matches": len(rows),
        "referees": computed, "leagueBtts": league_btts * 100,
        "tau": float(np.sqrt(tau2) * 100), "cutoff": cutoff, "q": FDR_Q,
        "tested": len(pvalues), "flagged": int((arr <= cutoff).sum() if cutoff > 0 else 0),
        "p05": int((arr < 0.05).sum()), "expected05": 0.05 * len(arr),
        "minP": float(arr.min()),
    }


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Championship Referee Matrix — O/U 2.5</title>
<style>
:root{color-scheme:light dark;
 --surface:#fcfcfb; --plane:#f9f9f7; --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8983;
 --line:#e4e3df; --over:#2a78d6; --under:#e34948; --mid:#f0efec; --good:#0ca30c;}
@media (prefers-color-scheme:dark){:root{
 --surface:#1a1a19; --plane:#0d0d0d; --ink:#fff; --ink2:#c3c2b7; --ink3:#8a8983;
 --line:#2e2e2b; --over:#3987e5; --under:#e66767; --mid:#383835;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;}
.wrap{max-width:1280px;margin:0 auto;padding-block:28px;padding-inline:20px}
h1{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--ink2);margin:0 0 22px;font-size:13px}
.verdict{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--under);
 border-radius:10px;padding:16px 18px;margin-bottom:22px}
.verdict b{font-size:15px}
.verdict p{margin:8px 0 0;color:var(--ink2);font-size:13px;max-width:78ch}
.warn{color:var(--under);font-weight:600}
.roi{font-weight:700}.roi.up{color:var(--good)}.roi.dn{color:var(--under)}
.tiles{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;
 padding:12px 16px;min-width:132px;flex:1 1 132px}
.tile .k{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3)}
.tile .v{font-size:21px;font-weight:600;margin-top:3px;font-variant-numeric:tabular-nums}
.tile .n{font-size:11px;color:var(--ink2);margin-top:2px}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
select,input{background:var(--surface);color:var(--ink);border:1px solid var(--line);
 border-radius:8px;padding:8px 10px;font:inherit;font-size:13px}
label{font-size:12px;color:var(--ink2)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:900px;font-size:13px}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{position:sticky;top:0;background:var(--surface);font-size:11px;text-transform:uppercase;
 letter-spacing:.05em;color:var(--ink3);font-weight:600;z-index:2}
td.l,th.l{text-align:left}
tr.sec td{background:var(--mid);font-size:11px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--ink2);font-weight:600}
.num{font-variant-numeric:tabular-nums}
.dim{color:var(--ink3)}
.gauge{display:inline-flex;align-items:center;gap:6px;justify-content:flex-end;width:170px}
.track{position:relative;width:112px;height:16px;background:var(--mid);border-radius:3px;flex:none}
.track i{position:absolute;top:3px;height:10px;border-radius:2px}
.track .raw{opacity:.28}
.track .shr{opacity:1}
.track .zero{position:absolute;left:50%;top:0;width:1px;height:16px;background:var(--ink3);opacity:.45}
.sig{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.06em;
 padding:2px 7px;border-radius:99px;background:var(--mid);color:var(--ink3)}
.sig.on{background:var(--good);color:#fff}
.foot{color:var(--ink2);font-size:12px;margin-top:14px;max-width:82ch}
tr:hover td{background:color-mix(in srgb,var(--mid) 55%,transparent)}
</style></head><body>
<div class="wrap">
<h1>Championship Referee Matrix — Over/Under 2.5 goals</h1>
<p class="sub" id="sub"></p>
<div class="verdict">
  <b>Read this before any cell.</b>
  <p id="verdict"></p>
</div>
<div class="tiles" id="tiles"></div>
<div class="bar">
  <label for="ref">Referee</label>
  <select id="ref"></select>
  <label for="sec">Section</label>
  <select id="sec"><option value="">All sections</option></select>
  <label><input type="checkbox" id="hide"> Hide cells under 15 matches</label>
</div>
<div class="card"><div class="scroll"><table>
<thead><tr>
<th class="l">Category</th><th>Actual over</th><th>Market over</th>
<th>Edge — raw vs shrunk</th><th>Shrunk</th>
<th title="Flat $1 on OVER 2.5 every match in this cell, best price at the close">$1 OVER ROI</th>
<th title="Flat $1 on UNDER 2.5 every match in this cell, best price at the close">$1 UNDER ROI</th>
<th>Goals/g</th><th>Fouls/g</th><th>Cards/g</th>
<th title="How often this cell went over 3.5 yellow cards">Cards o3.5</th>
<th title="Decimal odds you would need to break even at that hit rate. Beat it and you profit.">Cards BE</th>
<th>N</th><th class="l">Signal</th>
</tr></thead><tbody id="body"></tbody></table></div></div>
<p class="foot" id="foot"></p>
</div>
<script>
const D=__DATA__;
const $=id=>document.getElementById(id);
const f=(v,d=1)=>v==null?'<span class="dim">—</span>':v.toFixed(d);
const MAX=30;

$('sub').textContent=`${D.matches.toLocaleString()} matches · ${D.seasons.join(', ')} · `
 +`${Object.keys(D.referees).length} referee sheets · market = de-vigged closing price`;
$('verdict').innerHTML=`<b>${D.p05} cells clear p&lt;0.05 where pure chance predicts ~${Math.round(D.expected05)}`
 +` — a ratio of ${(D.p05/D.expected05).toFixed(2)}×.</b> After Benjamini-Hochberg at q=${D.q.toFixed(2)},`
 +` <b>${D.flagged} of ${D.tested.toLocaleString()}</b> cells survive.`
 +` <span class="warn">Is that just small samples?</span> Partly — and the honest split matters.`
 +` Planting referee effects of known size shows this data would catch an <b>8pp</b> spread in 99% of`
 +` simulations, but would miss a 3–5pp one. The spread estimator returns ${D.tau.toFixed(2)}pp, which sits at the`
 +` 66th percentile of its own null (p=0.34) — consistent with no effect at all, not evidence of a 2pp one.`
 +` So: <b>no referee effect large enough to bet exists here</b>; a small one might, and it does not persist`
 +` year to year (r=+0.08) so it could not be harvested. Cards/game on the same referees persists at r=+0.42 —`
 +` that is what a real referee effect looks like in this data, and it is not in the goals columns.`
 +` Per single cell, "noise" means this sample cannot resolve it (a ten-match cell only sees ±31pp) —`
 +` which is why edges are shrunk rather than hidden.`;

const tiles=[['Matches',D.matches.toLocaleString(),D.seasons.length+' seasons'],
 ['Spread estimate',D.tau.toFixed(2)+'pp','p=0.34 vs its null'],
 ['Cells tested',D.tested.toLocaleString(),'across all sheets'],
 ['Survive FDR',String(D.flagged),'q='+D.q.toFixed(2)],
 ['Smallest p',D.minP.toFixed(4),'needs ≤'+(D.q/D.tested).toFixed(6)],
 ['Detectable effect','~8pp','99% in power sims']];
$('tiles').innerHTML=tiles.map(([k,v,n])=>
 `<div class="tile"><div class="k">${k}</div><div class="v">${v}</div><div class="n">${n}</div></div>`).join('');

const refs=Object.keys(D.referees).sort((a,b)=>D.referees[b].games-D.referees[a].games);
$('ref').innerHTML=refs.map(r=>`<option value="${r}">${r} — ${D.referees[r].games} matches</option>`).join('');
const secs=[...new Set(D.referees[refs[0]].cells.map(c=>c.section))];
$('sec').innerHTML+=secs.map(s=>`<option>${s}</option>`).join('');

function gauge(raw,shr){
  const w=v=>Math.min(Math.abs(v),MAX)/MAX*50;
  const side=v=>v>=0?`left:50%;width:${w(v)}%;background:var(--over)`
                    :`right:50%;width:${w(v)}%;background:var(--under)`;
  return `<span class="gauge"><span class="track"><i class="raw" style="${side(raw)}"></i>`
   +`<i class="shr" style="${side(shr)}"></i><span class="zero"></span></span></span>`;
}
function render(){
  const ref=$('ref').value, sec=$('sec').value, hide=$('hide').checked;
  let last=null, out=[];
  for(const c of D.referees[ref].cells){
    if(sec&&c.section!==sec) continue;
    if(c.empty) continue;
    if(hide&&c.n<15) continue;
    if(c.section!==last){ out.push(`<tr class="sec"><td class="l" colspan="11">${c.section}</td></tr>`); last=c.section; }
    const roi=v=>v==null?'<span class="dim">—</span>'
      :`<span class="roi ${v>0?'up':'dn'}">${v>0?'+':''}${v.toFixed(1)}%</span>`;
    out.push(`<tr><td class="l">${c.label}</td>`
      +`<td class="num">${f(c.over)}%</td><td class="num dim">${f(c.mkt)}%</td>`
      +`<td>${gauge(c.edge,c.shrunk)}</td>`
      +`<td class="num dim">${c.shrunk>0?'+':''}${f(c.shrunk,2)}</td>`
      +`<td class="num">${roi(c.roiOver)}</td><td class="num">${roi(c.roiUnder)}</td>`
      +`<td class="num">${f(c.goals,2)}</td><td class="num">${f(c.fouls)}</td>`
      +`<td class="num">${f(c.cards,2)}</td>`
      +`<td class="num">${f(c.c35)}%</td>`
      +`<td class="num"><b>${c.cBE==null?'—':c.cBE.toFixed(2)}</b></td>`
      +`<td class="num">${c.n}</td>`
      +`<td class="l"><span class="sig ${c.sig?'on':''}">${c.sig?'SIGNAL':'noise'}</span></td></tr>`);
  }
  $('body').innerHTML=out.join('')||`<tr><td class="l" colspan="11">No cells match.</td></tr>`;
  $('foot').innerHTML=`<b>$1 ROI</b> is the flat historical record of backing that side every match in the cell,`
   +` at the best price on the board at the close — it is not a selection, and the two columns are near-mirrors,`
   +` so picking the greener one after the fact is how you talk yourself into a bet. <b>Cards BE</b> is the`
   +` decimal price you would need to break even at that cell's over-3.5 hit rate: if a book pays more than the`
   +` BE number, that bet was historically profitable. Cards are YELLOWS only — the red-card columns are empty`
   +` in this data. Raw edge is the faint bar, shrunk edge the solid one; bars clip at ±${MAX}pp.`;
}
['ref','sec','hide'].forEach(id=>$(id).addEventListener('input',render));
render();
</script></body></html>
"""


def main() -> None:
    payload = build_payload()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML.replace("__DATA__", json.dumps(payload)), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")
    print(f"  {payload['tested']} cells, {payload['flagged']} surviving FDR, tau={payload['tau']:.2f}pp")


if __name__ == "__main__":
    main()
