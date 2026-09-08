"""Build an auditable, frozen research input from downloaded sources."""
from pathlib import Path
from datetime import datetime, timezone
import json, re, hashlib
import pandas as pd
from bs4 import BeautifulSoup

P=Path(__file__).parent
UEFA='https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/'
SLOVAN='https://www.skslovan.com/zapasy/index.php?season=202627'
MADRID='https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/entrenamientos/el-equipo-se-esta-entrenando-07-09-2026'
PRESS='https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/ruedas-de-prensa/mourinho-07-09-2026'
DIMARCO='https://www.gazzetta.it/en/football/teams/inter/news/07-09-2026/dimarco-injury-wing-back-misses-real-madrid-clash.shtml'
# news heading, source league, domestic name, model identity
TEAMS=[
('AEK Athens','G1','AEK','aek-athen'),('LASK','AUT','LASK',None),
('Club Brugge','B1','Club Brugge','club-brugge-kv'),('Aston Villa','E0','Aston Villa','aston-villa-fc'),
('B. Dortmund','D1','Dortmund','borussia-dortmund'),('Villarreal','SP1','Villarreal','villarreal-cf'),
('Porto','P1','Porto','fc-porto'),('Man City','E0','Man City','manchester-city-fc'),
('Lille','F1','Lille','lille-osc'),('Real Betis','SP1','Betis',None),
('Real Madrid','SP1','Real Madrid','real-madrid-cf'),('Inter','I1','Inter','fc-internazionale-milano'),
('Barcelona','SP1','Barcelona','fc-barcelona'),('Feyenoord','N1','Feyenoord','feyenoord-rotterdam'),
('Stuttgart','D1','Stuttgart','vfb-stuttgart'),('Viking','NOR','Viking',None),
('Liverpool','E0','Liverpool','liverpool-fc'),('Atleti','SP1','Ath Madrid','club-atl-tico-de-madrid'),
('Paris','F1','Paris SG','paris-saint-germain-fc'),('Slovan Bratislava','manual','Slovan','k-slovan-bratislava'),
('Sporting CP','P1','Sp Lisbon','sporting-clube-de-portugal'),('Galatasaray','T1','Galatasaray','galatasaray-sk'),
('Napoli','I1','Napoli','ssc-napoli'),('Arsenal','E0','Arsenal','arsenal-fc')]
ROLES={
'Ordóñez':'CB','Goretzka':'CM','Manzambi':'CM','Adeniran':'ST','Kalajdžić':'ST',
'Raúl Asencio':'CB','Camavinga':'DM','Endrick':'ST','Arda Güler':'AM','Éder Militão':'CB','Thiago Pitarch':'CM','Rodrygo':'RW','Bernardo Silva':'AM','Tchouaméni':'DM','Mendy':'LB','Dimarco':'WB',
'Bensebaini':'CB','Schlotterbeck':'CB','Mane':'CB','Foyth':'CB','Bednarek':'CB','Froholdt':'CM','Pietuszewski':'LW','Samu':'ST','Sanusi':'LB','Doku':'LW',"O'Reilly":'LB',
'Nianzou':'CB','Diego Conde':'GK','Abde Ezzalzouli':'LW','Diego Llorente':'CB','Lo Celso':'AM','Aitor Ruibal':'RB',
'De Jong':'CM','Eric García':'CB','Bos':'LB','Moder':'CM','Nieuwkoop':'RB','Smal':'LB','Hadj Moussa':'RW',
'Jaquez':'CB','Nartey':'CM','Seimen':'GK','Tiago Tomás':'FW','Assignon':'RB','Berisha':'ST','Baertelsen':'CB','Bjørshol':'RB','Falchener':'CB','Haugen':'LB','Roseth':'CB',
'Bradley':'RB','Ekitiké':'ST','J.Gomez':'CB','Leoni':'CB','Arnau Ortiz':'LW','Sørloth':'ST','Nuno Santos':'WB','João Simões':'CM','Ba':'LW',
'Günay Güvenç':'GK','Lemina':'DM','Osimhen':'ST','Singo':'CB','McTominay':'CM','Saliba':'CB','Mosquera':'CB','Timber':'RB'}
DISPLAY={'B. Dortmund':'Borussia Dortmund','Man City':'Manchester City','Atleti':'Atlético de Madrid','Paris':'Paris Saint-Germain'}
now=datetime.now(timezone.utc).isoformat()
text=BeautifulSoup((P/'raw/uefa_team_news.html').read_text(),'html.parser').get_text('\n',strip=True).replace('\ufeff','')
parsed={}
for name,league,domestic,club in TEAMS:
    pattern=r'\n'+re.escape(name)+r'\nPossible line-up\n:(.*?)\nOut\n:(.*?)\nDoubtful\n:([^\n]*)'
    match=re.search(pattern,text,re.S)
    if not match: raise ValueError('Missing source team '+name)
    events=[]
    for state,part in [('out',match.group(2)),('doubtful',match.group(3))]:
        for item in part.strip().rstrip(',').split(','):
            item=item.strip()
            if not item or item.lower()=='none': continue
            player=item.split('(')[0].strip()
            if player not in ROLES: raise ValueError('Unreviewed player role '+player)
            events.append({'player':player,'status':state,'position':ROLES[player],'source_detail':item,'source':UEFA,'role_mapping':'manual broad-position research assumption; no player-specific valuation','retrieved_at_utc':now})
    if name=='Inter':
        events=[dict(e,status='out',source=DIMARCO,source_detail='Reported not travelling; supersedes earlier UEFA doubtful status') if e['player']=='Dimarco' else e for e in events]
    if name=='Real Madrid':
        events=[dict(e,status='doubtful',source=PRESS if e['player']=='Endrick' else MADRID,source_detail='Conflicting earlier injury report; training return / limited availability, scenario only') if e['player'] in ['Endrick','Thiago Pitarch'] else e for e in events]
        events.append({'player':'Mendy','status':'out','position':'LB','source':MADRID,'source_detail':'Club says rehabilitation continues','role_mapping':'manual broad-position research assumption','retrieved_at_utc':now})
    if league=='manual':
        rec=[('2026-08-01','Slovan','Podbrezova',3,0),('2026-08-15','Slovan','Ruzomberok',5,0),('2026-08-22','Kosice','Slovan',1,2),('2026-08-30','Slovan','Michalovce',1,2),('2026-09-05','DAC','Slovan',2,0)]
        d=pd.DataFrame(rec,columns=['Date','HomeTeam','AwayTeam','FTHG','FTAG']); source=SLOVAN
    else:
        d=pd.read_csv(P/f'raw/{league}.csv').rename(columns={'Home':'HomeTeam','Away':'AwayTeam','HG':'FTHG','AG':'FTAG'})
        source=f'https://football-data.co.uk/new/{league}.csv' if league in ['NOR','AUT'] else f'https://football-data.co.uk/mmz4281/2627/{league}.csv'
    d['Date']=pd.to_datetime(d.Date,dayfirst=league!='manual',utc=True)
    d=d[(d.Date>='2026-07-01')&(d.Date<pd.Timestamp(now))]
    d=d[(d.HomeTeam==domestic)|(d.AwayTeam==domestic)].sort_values('Date').tail(5)
    results=[]
    for _,r in d.iterrows():
        gf,ga=(r.FTHG,r.FTAG) if r.HomeTeam==domestic else (r.FTAG,r.FTHG)
        results.append({'date':r.Date.date().isoformat(),'home':r.HomeTeam,'away':r.AwayTeam,'home_goals':int(r.FTHG),'away_goals':int(r.FTAG),'points':3 if gf>ga else 1 if gf==ga else 0,'source':source})
    if name=='Viking':
        results.append({'date':'2026-09-04','home':'Sandefjord','away':'Viking','home_goals':1,'away_goals':1,'points':1,'source':'https://vikingstadion.no/nyheter'})
        results=results[-5:]
    latest=results[-1]['date']
    if name=='LASK': latest='2026-09-05' # Cup later than the latest domestic-league row.
    parsed[DISPLAY.get(name,name)]={'club_id':club,'league':league,'domestic_name':domestic,'league_results':results,'league_form_points':sum(r['points'] for r in results),'form_matches':len(results),'latest_competitive_date':latest,'rest_source':'https://www.lask.at/en/m/matches/pros/fixtures/2026-2027' if name=='LASK' else results[-1]['source'],'availability':events,'predicted_lineup_source':UEFA,'predicted_not_confirmed':True,'data_as_of_utc':now}
fixtures=json.loads((P.parent/'2026-09-08_md1_audit/audit.json').read_text())['rows']
for i,r in enumerate(fixtures):
    r['kickoff_utc']=r['european_match_date']+('T16:45:00Z' if i in [0,1,6,7] else 'T19:00:00Z')
    r['home_context']=parsed[r['home']];r['away_context']=parsed[r['away']]
    for side in ['home_context','away_context']:
        c=r[side]
        c['rest_days']=(pd.Timestamp(r['european_match_date']).date()-pd.Timestamp(c['latest_competitive_date']).date()).days
    for k in ['tiers','diagnostic_prices','diagnostic_probabilities','history_coverage','shared_engine_adjustments','baseline_status','totals_status','all_tiers_priced','live_status']: r.pop(k,None)
manifest={'cutoff_utc':now,'status':'researched_scenario_not_production_promotion','fixture_source':'https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-league-phase-fixtures/','notes':['Only current-season competitive domestic league matches enter form; friendlies excluded.','For fewer than five league games, unplayed slots contribute neutral 1.5 points, an explicit shrinkage assumption, not invented match results.','Rest is calendar-date difference to latest verified competitive club match; no claim of precise recovery hours.','Research availability uses broad-position legacy football weights; it is not the trained UCL player shadow.','Confirmed absences enter the central scenario. Doubtful and disputed players enter separate sensitivity scenarios.','Current domestic corners are archived but not added to 1X2; the separate corner challenger is not promoted.'],'fixtures':fixtures,'raw_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (P/'raw').iterdir() if p.is_file()}}
(P/'context.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
print('Saved',len(fixtures),'fixtures,',len(parsed),'teams,',sum(len(c['availability']) for c in parsed.values()),'availability events')
for name,c in parsed.items(): print(name,c['league_form_points'],c['form_matches'],c['latest_competitive_date'])
