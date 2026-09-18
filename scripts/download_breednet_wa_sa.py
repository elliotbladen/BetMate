#!/usr/bin/env python3
"""Independent dated result fallback for WA/SA metropolitan Saturdays."""
import concurrent.futures as cf, datetime as dt, hashlib, json, pathlib, urllib.error, urllib.request
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parents[1]/'data'/'raw'/'wa_sa_saturday'/'breednet'
TRACKS={'ascot':'ascot','belmont-park':'belmont','morphettville':'morphettville','morphettville-parks':'morphettville-parks'}
START=dt.date(2023,9,18); END=dt.date(2026,9,18); UA='BetMate-racing-archive/1.0'
def fetch(x):
 track,d=x; url=f'https://www.breednet.com.au/race-results/australia/{TRACKS[track]}/{d}'
 try:
  r=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=30); st,b=r.status,r.read()
 except urllib.error.HTTPError as e: st,b=e.code,e.read()
 except Exception as e: st,b=0,str(e).encode()
 p=ROOT/track/(str(d)+'.html'); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
 txt=BeautifulSoup(b,'html.parser').get_text(' ',strip=True)
 return {'track':track,'date':str(d),'url':url,'status':st,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'has_race_headers':('raceheader' in str(b).lower()),'has_barriers':('barrier' in txt.lower()),'has_margins':('margin' in txt.lower()),'has_sectionals':('sectional' in txt.lower()),'has_stewards':('steward' in txt.lower())}
def main():
 dates=[]; d=START+dt.timedelta(days=(5-START.weekday())%7)
 while d<=END: dates.append(d); d+=dt.timedelta(days=7)
 with cf.ThreadPoolExecutor(max_workers=8) as ex: records=list(ex.map(fetch,((t,d) for t in TRACKS for d in dates)))
 (ROOT/'manifest.json').write_text(json.dumps({'coverage_start':str(START),'coverage_end':str(END),'records':records},indent=2)+'\n')
 print(json.dumps({'requests':len(records),'http_200':sum(x['status']==200 for x in records),'race_pages':sum(x['has_race_headers'] for x in records)},indent=2))
if __name__=='__main__': main()
