"""Apply the EFL-style net +5 confluence rule to Week 1 UCL 1X2 picks."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/ucl/markets/ucl_combined_1x2_ou25_matrix.csv'
PRICES=ROOT/'outputs/football/ucl/2026-27/md01/_supporting/week_1_shadow_player_rating/prices.json'
OUT=ROOT/'outputs/football/ucl/2026-27/md01/_supporting/week_1_shadow_player_rating/matrix_net5_1x2.json'
EDGE=7.5; REQUIRED=5; MIN_SAMPLE=5

NAMES={'AEK Athens':'aek-athen','LASK':'lask-linz','Club Brugge':'club-brugge-kv','Aston Villa':'aston-villa-fc','Borussia Dortmund':'borussia-dortmund','Villarreal':'villarreal-cf','Porto':'fc-porto','Manchester City':'manchester-city-fc','Lille':'lille-osc','Real Betis':'real-betis','Real Madrid':'real-madrid-cf','Inter':'fc-internazionale-milano','Barcelona':'fc-barcelona','Feyenoord':'feyenoord-rotterdam','Stuttgart':'vfb-stuttgart','Viking':'viking-fk','Liverpool':'liverpool-fc','Atlético de Madrid':'club-atl-tico-de-madrid','Paris Saint-Germain':'paris-saint-germain-fc','Slovan Bratislava':'k-slovan-bratislava','Sporting CP':'sporting-clube-de-portugal','Galatasaray':'galatasaray-sk','Napoli':'ssc-napoli','Arsenal':'arsenal-fc'}

def market_probs(r):
    vals=[r.market_home_prob,r.market_draw_prob,r.market_away_prob]
    return vals if all(pd.notna(vals)) else None

def result_for(r,team):
    if r.home_team==team:return r.result
    return 'H' if r.result=='A' else ('A' if r.result=='H' else 'D')

def enrich(rows):
    histories=defaultdict(list)
    teams=set(rows.home_team)|set(rows.away_team)
    for team in teams:
        rows[f'previous__{team}']=None
        rows[f'rest__{team}']=None
    for i,r in rows.sort_values(['Date','match_id']).iterrows():
        for team in (r.home_team,r.away_team):
            prev=histories[team][-1] if histories[team] else None
            rows.at[i,f'previous__{team}']=result_for(prev,team) if prev is not None else None
            rows.at[i,f'rest__{team}']=(r.Date-prev.Date).days if prev is not None else None
            histories[team].append(r)
    return rows

def categories(rows,team,home,away,played):
    games=rows[(rows.home_team==team)|(rows.away_team==team)]
    previous=games.get(f'previous__{team}',pd.Series(index=games.index,dtype=object))
    rest=games.get(f'rest__{team}',pd.Series(index=games.index,dtype=float))
    opponent=away if team==home else home
    return [('All games',games),('Home games',games[games.home_team==team]),('Away games',games[games.away_team==team]),
            (played.strftime('%A'),games[games.Date.dt.weekday==played.weekday()]),('September',games[games.Date.dt.month==9]),
            ('After a win',games[previous=='H']),('After a draw',games[previous=='D']),('After a loss',games[previous=='A']),
            ('Short rest',games[rest<=3]),('Normal rest',games[rest.between(4,8)]),
            (f'vs {opponent}',games[(games.home_team==opponent)|(games.away_team==opponent)])]

def signal_stats(games,team):
    games=games[games.market_home_prob.notna()]
    if len(games)<MIN_SAMPLE:return None
    win=((games.apply(lambda r:(r.home_team==team and r.result=='H') or (r.away_team==team and r.result=='A'),axis=1)).mean()*100)
    implied=games.apply(lambda r:r.market_home_prob if r.home_team==team else r.market_away_prob,axis=1).mean()*100
    return win-implied,len(games)

def main():
    d=pd.read_csv(SOURCE);d['Date']=pd.to_datetime(d.Date,utc=True);d['result']=d.apply(lambda r:'H' if r.home_goals>r.away_goals else ('A' if r.home_goals<r.away_goals else 'D'),axis=1)
    d=enrich(d[d.season.isin(['2024-25','2025-26'])].copy())
    prices=json.loads(PRICES.read_text()); output=[]
    for p in prices['rows']:
        home,away=p['home'],p['away']; h,a=NAMES[home],NAMES[away]; base=p.get('normal');
        if not base: output.append({'home':home,'away':away,'status':'BLOCKED','net':None,'aligned':[],'opposed':[]});continue
        probs=base['probabilities']; pick=max(probs,key=probs.get); team=h if pick=='home' else (a if pick=='away' else None)
        # Draw is not a team signal; evaluate the two team directions against the draw pick separately.
        if team is None: output.append({'home':home,'away':away,'status':'DRAW_PICK_NOT_TEAM_CONFLUENCE','net':None,'aligned':[],'opposed':[]});continue
        aligned=[];opposed=[];played=datetime.fromisoformat(p['kickoff_utc'].replace('Z','+00:00')).date()
        for t in (team, a if team==h else h):
            for label,g in categories(d,t,h,a,played):
                s=signal_stats(g,t)
                if not s:continue
                edge,n=s; direction=1 if t==team else -1
                item={'team':t,'category':label,'edge_pp':round(edge,2),'n':n}
                if edge*direction>=EDGE:aligned.append(item)
                elif edge*direction<=-EDGE:opposed.append(item)
        net=len(aligned)-len(opposed)
        output.append({'home':home,'away':away,'normal_pick':pick,'status':'ASSESSED','aligned':aligned,'opposed':opposed,'net':net,'passes_net5':net>=REQUIRED})
    report={'generated_at_utc':datetime.utcnow().isoformat()+'Z','source':str(SOURCE.relative_to(ROOT)),'seasons':['2024-25','2025-26'],'edge_threshold_pp':EDGE,'required_net':REQUIRED,'minimum_sample':MIN_SAMPLE,'rule':'aligned signals minus opposed signals; categories are overlapping, not independent.','results':output,'teams_with_net5':[r for r in output if r.get('passes_net5')]}
    OUT.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'teams_with_net5':report['teams_with_net5'],'assessed':sum(r['status']=='ASSESSED' for r in output)},indent=2))

if __name__=='__main__':main()
