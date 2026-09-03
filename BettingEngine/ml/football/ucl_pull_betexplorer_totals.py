import csv, re, json, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2].parent
OUT=ROOT/'BettingEngine/data/ucl/markets/ucl_betexplorer_totals_2024_25.csv'
pages=['tmp_betexp_league2425.html','tmp_betexp_results_2425.html']
links=[]
pat=re.compile(r'href="([^"]*/champions-league-2024-2025/[^"?]+/[A-Za-z0-9]{8}/?)"')
for p in pages:
    s=(ROOT/p).read_text(encoding='utf-8',errors='ignore')
    links += [x for x in pat.findall(s) if '/results/' not in x]
links=list(dict.fromkeys(links))
def get(url):
    return urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html,application/xhtml+xml'}),timeout=30).read().decode('utf-8','ignore')

def one(path):
    try:
        u='https://www.betexplorer.com'+path
        eid=path.rstrip('/').split('/')[-1]
        # odds endpoint parameter is 1 for finished events
        ou=json.loads(get(f'https://www.betexplorer.com/match-odds/{eid}/1/ou/bestOdds/?lang=en'))['odds']
        # Restrict to handicap 2.50 table, then collect best rows. Values are final archive snapshot prices.
        block=re.search(r'<table data-handicap="2\.50".*?</table>',ou,re.S)
        if not block: return {'path':path,'event_id':eid,'error':'no_25'}
        b=block.group(0)
        rows=[]
        for row in re.findall(r'<tr\s+data-bid=.*?</tr>',b,re.S):
            bm=re.search(r'data-bid="(\d+)"',row); name=re.search(r'data-bookie="([^"]+)',row)
            vals=re.findall(r'class="[^"]*detail-odds[^\"]*"[^>]*data-odd="([0-9.]+)"[^>]*data-created="([^"]+)',row)
            if bm and len(vals)>=2: rows.append({'bid':bm.group(1),'bookmaker':name.group(1) if name else '', 'over':vals[0][0], 'over_created':vals[0][1], 'under':vals[1][0], 'under_created':vals[1][1]})
        return {'path':path,'event_id':eid,'rows':rows}
    except Exception as e: return {'path':path,'error':str(e)}

res=[]
with ThreadPoolExecutor(max_workers=6) as ex:
    fs=[ex.submit(one,p) for p in links]
    for i,f in enumerate(as_completed(fs),1):
        res.append(f.result())
        if i%25==0: print(i,'/',len(links),flush=True)

OUT.parent.mkdir(parents=True,exist_ok=True)
with OUT.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['path','event_id','bookmaker','over25','over_created','under25','under_created','error'])
    w.writeheader()
    for x in sorted(res,key=lambda z:z.get('path','')):
        for r in x.get('rows',[]): w.writerow({'path':x['path'],'event_id':x.get('event_id',''),'bookmaker':r['bookmaker'],'over25':r['over'],'over_created':r['over_created'],'under25':r['under'],'under_created':r['under_created'],'error':''})
        if not x.get('rows'): w.writerow({'path':x['path'],'event_id':x.get('event_id',''),'error':x.get('error','')})
print(json.dumps({'links':len(links),'responses':len(res),'with_rows':sum(bool(x.get('rows')) for x in res),'out':str(OUT)}))
