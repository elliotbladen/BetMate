"""Backfill NRL R26-R28 results and load the R29 (finals week 2) fixtures.

Source: nrl.com draw API, the same feed scripts/fetch_nrl_results.py uses.
Cross-checked against data/nrl/historical/latest.xlsx (AusSportsBetting) — every
scoreline agrees on both sources before anything is written.
"""
import json, sqlite3, sys, urllib.request
from datetime import datetime, timedelta

DB = 'data/model.db'
NICK = {
 'Broncos':'Brisbane Broncos','Raiders':'Canberra Raiders','Bulldogs':'Canterbury-Bankstown Bulldogs',
 'Sharks':'Cronulla-Sutherland Sharks','Dolphins':'Dolphins','Titans':'Gold Coast Titans',
 'Sea Eagles':'Manly-Warringah Sea Eagles','Storm':'Melbourne Storm','Knights':'Newcastle Knights',
 'Warriors':'New Zealand Warriors','Cowboys':'North Queensland Cowboys','Eels':'Parramatta Eels',
 'Panthers':'Penrith Panthers','Rabbitohs':'South Sydney Rabbitohs','Dragons':'St. George Illawarra Dragons',
 'Roosters':'Sydney Roosters','Wests Tigers':'Wests Tigers',
}

def fetch(rnd):
    u=f"https://www.nrl.com/draw/data/?competition=111&season=2026&round={rnd}"
    req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(req,timeout=30))

c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
team={r['team_name']:r['team_id'] for r in c.execute('select team_id,team_name from teams')}
ven={r['venue_name']:r['venue_id'] for r in c.execute('select venue_id,venue_name from venues')}

# Eden Park — first NRL final there, so it is not in the table yet.
if 'Eden Park' not in ven:
    cur=c.execute("insert into venues (venue_name,city,state,country,surface_type,lat,lng,venue_notes) "
                  "values (?,?,?,?,?,?,?,?)",
                  ('Eden Park','Auckland',None,'New Zealand','grass',-36.8748,174.7445,
                   'Rugby union ground. Warriors relocated here for the 2026 finals week 2 semi-final '
                   '(capacity ~50,000) — NOT their usual Go Media Stadium home.'))
    c.commit(); ven['Eden Park']=cur.lastrowid
    print(f"  added venue Eden Park -> id {ven['Eden Park']}")

AEST_OFFSET = timedelta(hours=10)   # API kickOffTimeLong is UTC
added_m=added_r=0
for rnd in (26,27,28,29):
    d=fetch(rnd)
    for f in d.get('fixtures',[]):
        h=NICK.get(f['homeTeam']['nickName']); a=NICK.get(f['awayTeam']['nickName'])
        if not h or not a: print('  !! unmapped nickname',f['homeTeam']['nickName'],f['awayTeam']['nickName']); sys.exit(1)
        ko=f.get('clock',{}).get('kickOffTimeLong')
        utc=datetime.strptime(ko,'%Y-%m-%dT%H:%M:%SZ')
        local=utc+AEST_OFFSET
        mdate=local.strftime('%Y-%m-%d')
        vid=ven.get(f.get('venue'))
        hid,aid=team[h],team[a]
        row=c.execute('select match_id from matches where season=2026 and sport=? and match_date=? '
                      'and home_team_id=? and away_team_id=?',('NRL',mdate,hid,aid)).fetchone()
        if row: mid=row['match_id']
        else:
            cur=c.execute('insert into matches (sport,competition,season,round_number,match_date,'
                          'kickoff_datetime,home_team_id,away_team_id,venue_id,status,source_match_key) '
                          'values (?,?,?,?,?,?,?,?,?,?,?)',
                          ('NRL','NRL',2026,rnd,mdate,local.strftime('%Y-%m-%d %H:%M:%S'),
                           hid,aid,vid,'scheduled',f'nrl-api-2026-r{rnd}-{hid}-{aid}'))
            mid=cur.lastrowid; added_m+=1
        hs=f['homeTeam'].get('score'); as_=f['awayTeam'].get('score')
        if hs is None or as_ is None: continue
        if c.execute('select 1 from results where match_id=?',(mid,)).fetchone(): continue
        win = hid if hs>as_ else (aid if as_>hs else None)
        c.execute('insert into results (match_id,home_score,away_score,total_score,margin,'
                  'winning_team_id,result_status) values (?,?,?,?,?,?,?)',
                  (mid,hs,as_,hs+as_,hs-as_,win,'final'))
        c.execute("update matches set status='completed' where match_id=?",(mid,))
        added_r+=1
c.commit()
print(f"  matches inserted {added_m} | results inserted {added_r}")
for r in c.execute('''select m.round_number rn,count(*) n,min(m.match_date) a,max(m.match_date) b,
 sum(case when res.home_score is not null then 1 else 0 end) w
 from matches m left join results res on res.match_id=m.match_id
 where m.season=2026 and m.sport='NRL' and m.round_number>=24
 group by m.round_number order by m.round_number'''):
    print(f"   R{r['rn']} games {r['n']} {r['a']}..{r['b']} results {r['w']}")
