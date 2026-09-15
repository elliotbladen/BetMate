"""Reproduce the research report from frozen model files and cited quote endpoints."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / 'BettingEngine/outputs/football/ucl/2026-27/md01/_supporting'
FIRST = BASE / 'week_1_shadow_player_rating/prices.csv'
LAST = BASE / 'week_1_champions_league_prices/md1_remaining_normal_and_shadow/run/normal/prices.csv'

def read(path):
    return list(csv.DictReader(path.open()))

def dec(value):
    a = float(value)
    assert abs(a) >= 100
    return 1 + (a / 100 if a > 0 else 100 / -a)

def profit(odds, won):
    return odds - 1 if won else -1

def write(name, rows):
    with (HERE / name).open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def main():
    meta = json.loads((HERE / 'sources.json').read_text())
    quotes = read(HERE / 'quote_endpoints.csv')
    alias = {'Paris Saint-Germain':'Paris Saint Germain', 'Sporting CP':'Sporting Lisbon', 'Slavia Prague':'Slavia Praha'}
    models = []
    for r in read(FIRST):
        if not r['normal_home']: continue
        models.append(dict(home=r['home'], away=r['away'], fair={s:float(r['normal_'+s]) for s in ('home','draw','away')}, source=str(FIRST.relative_to(ROOT)), totals=None))
    for r in read(LAST):
        if not r['home_fair_odds']: continue
        models.append(dict(home=r['home'], away=r['away'], fair={s:float(r[s+'_fair_odds']) for s in ('home','draw','away')}, source=str(LAST.relative_to(ROOT)), totals={'over':float(r['over25_fair_odds_raw']), 'under':float(r['under25_fair_odds_raw'])}))
    assert len(models) == 12
    bets, comparisons, totals = [], [], []
    for m in models:
        home = alias.get(m['home'],m['home'])
        src = next(r for r in meta['fixtures'] if r['home_feed']==home)
        close = [r for r in quotes if r['home']==home and r['market']=='ml' and r['book']=='pinnacle' and r['anchor']=='last_available_pregame']
        assert len(close)==3
        odds = {r['side']:dec(r['american_odds']) for r in close}
        vig = sum(1/o for o in odds.values())
        assert 0.99 < vig < 1.2
        outcome = 'home' if src['home_goals']>src['away_goals'] else 'away' if src['away_goals']>src['home_goals'] else 'draw'
        pick = min(m['fair'],key=m['fair'].get)
        for s, fair in m['fair'].items():
            opening = src['opening_'+s+'_american']
            opening = dec(opening) if opening is not None else None
            comparisons.append(dict(home=m['home'],away=m['away'],selection=s,model_fair=fair,opening_odds=opening,closing_odds=odds[s],model_edge_open_pct=100*(opening/fair-1) if opening else None,model_edge_close_pct=100*(odds[s]/fair-1),model_minus_close_fair_pp=100*(1/fair-(1/odds[s])/vig),opening_to_close_clv_pct=100*(opening/odds[s]-1) if opening else None,opening_quote_time='not supplied',closing_quote_time=close[0]['snapshot_ts'],source_url=src['opening_source']))
        c = comparisons[-3+('home','draw','away').index(pick)]
        assert c['selection']==pick and c['home']==m['home']
        assert c['opening_odds'] is not None
        won = pick==outcome
        bets.append(dict(home=m['home'],away=m['away'],selection=pick,model_fair=c['model_fair'],opening_odds=c['opening_odds'],closing_odds=c['closing_odds'],clv_pct=c['opening_to_close_clv_pct'],closing_fair_clv_pct=100*(c['opening_odds']*(1/c['closing_odds'])/vig-1),result=f"{src['home_goals']}-{src['away_goals']}",won=won,stake=1,opening_profit=profit(c['opening_odds'],won),closing_profit=profit(c['closing_odds'],won),model_source=m['source']))
        if m['totals'] is None:
            totals.append(dict(home=m['home'],away=m['away'],status='NO_FINAL_FROZEN_TOTAL_PRICE',selection=None,model_fair=None,result=f"{src['home_goals']}-{src['away_goals']}",won=None,book=None,earliest_available_odds=None,last_available_odds=None,earliest_quote_time=None,last_quote_time=None,last_quote_minutes_before_kickoff=None,earliest_profit=None,last_profit=None))
            continue
        pick = min(m['totals'],key=m['totals'].get)
        won = (src['home_goals']+src['away_goals']>2.5)==(pick=='over')
        candidates = [r for r in quotes if r['home']==home and r['market']=='total' and r['line']=='2.5' and r['side']==pick]
        # Fixed book priority, independent of prices and match outcomes. Sportsbooks only.
        book = next((b for b in ('pinnacle','betmgm','betonlineag','ballybet','betrivers','betparx','bovada','fliff','lowvig') if any(r['book']==b for r in candidates)),None)
        early = next((r for r in candidates if r['book']==book and r['anchor']=='earliest_available'),None)
        late = next((r for r in candidates if r['book']==book and r['anchor']=='last_available_pregame'),None)
        eo,lo = (dec(early['american_odds']),dec(late['american_odds'])) if early else (None,None)
        minutes=(datetime.fromisoformat(late['commence_time'].replace('Z','+00:00'))-datetime.fromisoformat(late['snapshot_ts'])).total_seconds()/60 if late else None
        totals.append(dict(home=m['home'],away=m['away'],status='FROZEN_RAW_TOTAL_WITH_QUOTES' if book else 'FROZEN_RAW_TOTAL_MISSING_2_5_QUOTES',selection=pick,model_fair=m['totals'][pick],result=f"{src['home_goals']}-{src['away_goals']}",won=won,book=book,earliest_available_odds=eo,last_available_odds=lo,earliest_quote_time=early['snapshot_ts'] if early else None,last_quote_time=late['snapshot_ts'] if late else None,last_quote_minutes_before_kickoff=minutes,earliest_profit=profit(eo,won) if eo else None,last_profit=profit(lo,won) if lo else None))
    write('all_1x2_comparisons.csv',comparisons)
    write('one_dollar_1x2.csv',bets)
    write('totals_coverage.csv',totals)
    n=len(bets)
    summary={'bets':n,'wins':sum(b['won'] for b in bets),'stake':n,'opening_return':sum(b['opening_profit']+1 for b in bets),'closing_return':sum(b['closing_profit']+1 for b in bets),'opening_profit':sum(b['opening_profit'] for b in bets),'closing_profit':sum(b['closing_profit'] for b in bets),'mean_raw_clv_pct':sum(b['clv_pct'] for b in bets)/n,'mean_margin_removed_clv_pct':sum(b['closing_fair_clv_pct'] for b in bets)/n,'model_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (FIRST,LAST)}}
    for anchor in ('opening','closing'):summary[anchor+'_roi_pct']=100*summary[anchor+'_profit']/n
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# UCL matchday 1: opening, closing and $1 model selections','', 'Research date: 15 September 2026. Normal model; 90-minute markets. One $1 bet per modelled match on its most likely 1X2 outcome, regardless of value. Six blocked fixtures are excluded, with no invented selections.','', '## 1X2 results','', '| Entry price | Bets | Wins | Staked | Returned | Profit | ROI |','|---|---:|---:|---:|---:|---:|---:|']
    for a in ('opening','closing'):lines.append(f"| Pinnacle {a} | {n} | {summary['wins']} | ${n:.2f} | ${summary[a+'_return']:.2f} | ${summary[a+'_profit']:+.2f} | {summary[a+'_roi_pct']:+.2f}% |")
    lines += ['',f"Mean opening-to-close CLV: **{summary['mean_raw_clv_pct']:+.2f}%** using quoted odds, or **{summary['mean_margin_removed_clv_pct']:+.2f}%** against the proportional margin-removed closing probabilities.",'','| Match | Pick | Model fair | Open | Close | CLV | Score | Open P/L | Close P/L |','|---|---|---:|---:|---:|---:|---|---:|---:|']
    for b in bets:lines.append(f"| {b['home']} – {b['away']} | {b['selection']} | {b['model_fair']:.2f} | {b['opening_odds']:.3f} | {b['closing_odds']:.3f} | {b['clv_pct']:+.2f}% | {b['result']} | {b['opening_profit']:+.3f} | {b['closing_profit']:+.3f} |")
    lines += ['','## O/U 2.5: incomplete coverage','', 'Only **three final frozen raw O/U predictions** were found: PSV Over (lost), Bayern Over (won), Slavia Under (lost). Nine final first-slate predictions explicitly withheld totals. The older audit contains totals from a failed/nonconverged baseline; those are not substituted. The previous top-level report incorrectly described 12 frozen totals prices.','', 'The export has no exact 2.5 quotes for PSV or Bayern. Slavia has BetMGM Under 2.5 at the endpoints below. These do not establish a true market opener. A full totals ROI or opening-to-close CLV cannot be reported.','', '| Match | Model pick | Model fair | Outcome | Earliest available | Last available | Book |','|---|---|---:|---|---:|---:|---|']
    for t in totals:
        if t['selection']:
            lines.append(f"| {t['home']} – {t['away']} | {t['selection']} 2.5 | {t['model_fair']:.3f} | {'Won' if t['won'] else 'Lost'} | {t['earliest_available_odds'] or 'Missing'} | {t['last_available_odds'] or 'Missing'} | {t['book'] or 'Missing'} |")
    lines += ['', 'For the three saved totals selections, $3 would be staked. Total return equals the Bayern Over 2.5 entry odds, because the other two bets lose. Profit = Bayern odds − $3; ROI = (Bayern odds − 3) / 3. Its missing quote prevents a numeric answer. A combined 1X2 + totals ROI would therefore also be incomplete.','', '## Definitions and limits','', '- Decimal-odds CLV = opening odds / closing odds − 1. Positive means the opening bettor secured a higher payout. This is hypothetical opening-entry CLV, not evidence of bets actually placed.', '- Margin-removed CLV = opening odds × closing fair probability − 1; closing fair probability = (1 / selection odds) / sum(1 / all three closing odds).', '- Model edge = market odds / model fair odds − 1. It measures model-implied expected return, not CLV. All 36 1X2 outcomes and both entry comparisons are in `all_1x2_comparisons.csv`.', '- ROI = net profit / total stake. A drawn match loses a home/away 1X2 bet. No commissions, bonuses, taxes or staking variation.', '- Openers are Pinnacle-labelled home/away prices transcribed from the cited game pages. Opening timestamps and draw prices are unavailable. No no-vig opening probability is invented.', '- Opening-price returns assume the later frozen model selections could be backed at those historical openers. Without opener timestamps, their availability after the model cutoff cannot be verified. This is a retrospective price benchmark, not an executable historical strategy.', '- Closing quotes use Pinnacle rows in the timestamped export, not the page’s best-book summary: that summary sometimes compares a Pinnacle opener with another bookmaker’s close.', '- The export was clamped to 8 September 07:35 UTC onward. First available quotes in it are not asserted to be opening quotes. The endpoint CSV retains quote times and market lines; snapshots after kickoff are excluded.', '- No frozen model rerun or retrospective fit was used. Prices remain provisional research outputs with thin/stale team-history limitations. Twelve matches cannot establish long-run profitability.', '- Missing selections: AEK–LASK, Lille–Betis, Stuttgart–Viking, Fenerbahçe–Roma, Como–Leipzig, Manchester United–Sabah.','', '## Sources and reproduction','', f"- [UEFA final results]({meta['result_source']})", '- [The Odds Gap export schema and access limits](https://theoddsgap.com/data). `sources.json` records the request, returned window and original export hash. `quote_endpoints.csv` preserves the scoped numerical records used here.']
    for src in meta['fixtures']:lines.append(f"- [{src['home_feed']} opening quote and closing page]({src['opening_source']})")
    lines += ['', 'Run `python3 reports/ucl/2026-27/md01/calculate.py` from the repository root. Uses Python standard library only. Frozen model input hashes are recorded in `summary.json`.','']
    (HERE/'README.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2))

if __name__ == '__main__':
    main()
