"""Resolve archived UEFA projected XIs against current ESPN team rosters."""
from pathlib import Path
import sys
import json
import re
import unicodedata
import hashlib
from datetime import datetime, timezone
import pandas as pd
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ml.football.ucl_player_features import player_prior

TEAM_ALIASES={'B. Dortmund':'Borussia Dortmund','Man City':'Manchester City','Inter':'Internazionale',
              'Porto':'FC Porto','Feyenoord':'Feyenoord Rotterdam','Stuttgart':'VfB Stuttgart',
              'Paris':'Paris Saint-Germain','Atleti':'Atlético Madrid','Viking':'Viking FK','LASK':'LASK Linz',
              'Atlético de Madrid':'Atlético Madrid'}


def normalize(name):
    name=name.translate(str.maketrans({'ø':'o','Ø':'O','ł':'l','Ł':'L','đ':'d','Đ':'D','ı':'i'}))
    return re.sub(r'[^a-z0-9 ]',' ', ''.join(c for c in unicodedata.normalize('NFKD',name.lower()) if not unicodedata.combining(c))).split()


def resolve(name, roster, goalkeeper=False):
    tokens=set(normalize(name))
    candidates=roster[roster.position_group.eq('GK') if goalkeeper else ~roster.position_group.eq('GK')]
    ids=[]
    for _,row in candidates.iterrows():
        full=normalize(row.player_name)
        if tokens and tokens.issubset(set(full)):ids.append(str(row.player_id))
    return sorted(set(ids))


def main():
    folder=ROOT/'data/ucl/player_layer'
    hist=pd.read_csv(folder/'prepared/audited_history.csv',dtype={'player_id':str,'event_id':str})
    hist['date']=pd.to_datetime(hist.kickoff,utc=True)
    hist=hist.sort_values(['date','event_id','player_id'])
    context=json.loads((ROOT/'outputs/football/ucl/2026-27/md01/_supporting/2026-09-08_researched/context.json').read_text())
    html=ROOT/'outputs/football/ucl/2026-27/md01/_supporting/2026-09-08_researched/raw/uefa_team_news.html'
    soup=BeautifulSoup(html.read_text(),'html.parser')
    projected={}
    for p in soup.find_all('p'):
        text=p.get_text(' ',strip=True)
        if not text.startswith('Possible line-up'):continue
        heading=p.find_previous_sibling('p')
        if heading is None:continue
        team=TEAM_ALIASES.get(heading.get_text(' ',strip=True),heading.get_text(' ',strip=True))
        part=text.split(':',1)[1].split('Out',1)[0].strip()
        names=[n.strip() for n in re.split('[;,]',part) if n.strip()]
        if len(names)==11:projected[team]=names
    # A later archived report explicitly names Carlos Augusto as Dimarco's replacement.
    dimarco_source='https://www.gazzetta.it/en/football/teams/inter/news/07-09-2026/dimarco-injury-wing-back-misses-real-madrid-clash.shtml'
    if 'Dimarco' in projected.get('Internazionale',[]):
        projected['Internazionale']=['Carlos Augusto' if n=='Dimarco' else n for n in projected['Internazionale']]
    cutoff=pd.Timestamp(datetime.now(timezone.utc))
    current_rosters={}
    for path in (folder/'rosters').glob('*.json'):
        if path.name.endswith('.meta.json'):continue
        data=json.loads(path.read_text())
        meta=json.loads(path.with_suffix('.meta.json').read_text())
        if pd.Timestamp(meta['retrieved_at_utc'])>cutoff:raise ValueError('Future roster observation')
        current_rosters[data['team']['displayName']]=(data,meta)
    overrides={(r['team'],r['name']):r for r in json.loads((folder/'player_name_overrides.json').read_text())}
    teams={}
    for fixture in context['fixtures']:
        if cutoff>=pd.Timestamp(fixture['kickoff_utc']):raise ValueError('Cannot create prematch snapshot after kickoff')
        for side in ('home','away'):
            name=fixture[side]; espn=TEAM_ALIASES.get(name,name)
            prior=hist[(hist.team==espn)&(hist.date<cutoff)]
            latest=prior.date.max()
            # Current team registry establishes identity; latest prior played position establishes role.
            roster_data,roster_meta=current_rosters[espn]
            registry=[]
            for athlete in roster_data['athletes']:
                pid=str(athlete['id'])
                role={'G':'GK','D':'DEF','M':'MID','F':'ATT'}.get(athlete.get('position',{}).get('abbreviation'),'UNKNOWN')
                played=hist[(hist.player_id==pid)&(hist.date<cutoff)&hist.position_group.isin(['GK','DEF','MID','ATT'])]
                if len(played):role=played.iloc[-1].position_group
                registry.append({'player_id':pid,'player_name':athlete['displayName'],'position_group':role})
            roster=pd.DataFrame(registry)
            players=[]; unresolved=[]
            for i,label in enumerate(projected.get(espn,[])):
                ids=resolve(label,roster,goalkeeper=i==0)
                override=overrides.get((espn,label))
                if override and override['player_id'] in set(roster.player_id):ids=[override['player_id']]
                if len(ids)!=1:
                    unresolved.append({'name':label,'candidate_ids':ids});continue
                player=roster[roster.player_id==ids[0]].iloc[0]
                history=player_prior(hist,ids[0],cutoff)
                players.append({'uefa_name':label,'player_id':ids[0],'player_name':player.player_name,
                    'position_group':player.position_group,'side':side,
                    'identity_method':'unique normalized name-token match within recent team rosters; goalkeeper separated',
                    'identity_override':override,
                    'lineup_source':dimarco_source if espn=='Internazionale' and label=='Carlos Augusto' else None,
                    'expected_minutes_share':min(1.,history['roll_minutes']/90) if history else None,
                    'expected_minutes_method':'prior-eight-roster-row mean; scenario estimate, not source observation',
                    'history':history})
            confirmed_out_conflicts=[]
            for e in fixture[side+'_context']['availability']:
                if e['status']!='out':continue
                for player in players:
                    tokens=normalize(e['player']);full=normalize(player['player_name'])
                    if (tokens[0]==full[-1] if len(tokens)==1 else set(tokens).issubset(set(full))):
                        confirmed_out_conflicts.append({'player_id':player['player_id'],'name':player['player_name'],'source':e['source']})
            teams[name]={'espn_team':espn,'latest_collected_match':str(latest),'projected_players':players,
                'unresolved':unresolved,'confirmed_out_conflicts':confirmed_out_conflicts,
                'status':'complete' if len(players)==11 and not unresolved and not confirmed_out_conflicts else 'requires_review',
                'roster_source':roster_meta,
                'available_recent_roster':roster[['player_id','player_name','position_group']].to_dict('records')}
    source=soup.find('link',rel='canonical')['href']
    payload={'cutoff_utc':str(cutoff),'source':source,
        'source_archive':str(html.relative_to(ROOT)),
        'source_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),
        'source_published_at_utc':'2026-09-07T12:46:00Z','source_modified_at_utc':'2026-09-07T21:45:19Z',
        'source_retrieved_at_utc':context['cutoff_utc'],'lineup_type':'uefa_predicted_not_confirmed',
        'teams':teams}
    (folder/'week1_projected_snapshot.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    for name,team in teams.items():
        print(name,team['status'],len(team['projected_players']),'unresolved',team['unresolved'],'out conflicts',team['confirmed_out_conflicts'])


if __name__=='__main__':main()
