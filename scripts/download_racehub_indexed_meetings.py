#!/usr/bin/env python3
"""Expand RaceHub's indexed Saturday meetings into every race page."""
import datetime as dt, hashlib, json, pathlib, re, urllib.request, urllib.error
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parents[1]/'data'/'raw'/'wa_sa_saturday'
TRACKS=['ascot','belmont-park','morphettville','morphettville-parks']
START=dt.date(2023,9,18); END=dt.date(2026,9,18)
UA='BetMate-racing-archive/1.0'
def get(url):
 try:
  r=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=30); return r.status,r.read()
 except urllib.error.HTTPError as e:return e.code,e.read()
 except Exception as e:return 0,str(e).encode()
def main():
 records=[]
 for track in TRACKS:
  status,body=get(f'https://racehub.com.au/tracks/{track}')
  (ROOT/track/'track-page.html').parent.mkdir(parents=True,exist_ok=True); (ROOT/track/'track-page.html').write_bytes(body)
  links=sorted(set(re.findall(rb'form-guide/horse-racing/'+track.encode()+rb'/([0-9]{4}-[0-9]{2}-[0-9]{2})/race-1',body)))
  for raw in links:
   d=dt.date.fromisoformat(raw.decode())
   if not START<=d<=END or d.weekday()!=5: continue
   for n in range(1,16):
    url=f'https://racehub.com.au/form-guide/horse-racing/{track}/{d}/race-{n}'
    st,b=get(url); text=BeautifulSoup(b,'html.parser').get_text(' ',strip=True)
    if 'Race Not Found' in text and n>1: break
    path=ROOT/track/str(d)/'racehub'/f'race-{n}.html'; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b)
    records.append({'track':track,'date':str(d),'race':n,'url':url,'status':st,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'has_sectionals':'sectional' in text.lower(),'has_stewards':'steward' in text.lower(),'race_not_found':'Race Not Found' in text})
 (ROOT/'racehub_indexed_manifest.json').write_text(json.dumps({'coverage_start':str(START),'coverage_end':str(END),'records':records},indent=2)+'\n')
 print('saved',len(records),'indexed RaceHub race pages')
if __name__=='__main__': main()
