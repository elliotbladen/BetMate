"""Bounded parallel completion of the Racing NSW source inventory."""
import json, sqlite3, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from .trial_racing_nsw import source_url, parse
from .trial_ingest import fetch, archive_payload
from .trial_calendar_expansion import digest
from .storage import utc_now
from .trial_official_archive import install

def main(plan, database, registry, archive, run, report, workers=4):
    plan=json.loads(Path(plan).read_text())["meetings"]
    meetings=[x for x in plan if x.get("state")=="NSW" and x.get("isTrial") and not x.get("isJumpOut")]
    run=Path(run); run.mkdir(parents=True,exist_ok=True); archive=Path(archive)
    pending=[]
    for item in meetings:
        url=source_url(item); p=run/(digest(url)+'.json')
        if p.exists() and json.loads(p.read_text()).get('status') in {'verified','failed','abandoned'}: continue
        pending.append((item,url,p))
    def get(entry):
        item,url,p=entry
        try:
            time.sleep(0.5)
            raw=fetch(url); a=archive_payload(archive,source_id='racing_nsw_trials',source_url=url,payload=raw,collected_at=utc_now())
            result=parse(raw,item,url,a['collected_at'])
            return entry,a,result,None
        except Exception as exc: return entry,None,None,str(exc)
    c=sqlite3.connect(database); inserted=processed=failed=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(get,e) for e in pending]
        for f in as_completed(futures):
            (item,url,p),a,result,error=f.result(); processed+=1
            if error:
                failed+=1; p.write_text(json.dumps({'meeting':item,'source_url':url,'status':'failed','error':error},indent=2)+'\n')
            else:
                n=install(c,result['rows'],a); inserted+=n
                p.write_text(json.dumps({'meeting':item,'source_url':url,'status':result['status'],'rows':len(result['rows']),'inserted':n},indent=2)+'\n')
            if processed%50==0: print(json.dumps({'processed':processed,'pending':len(pending),'inserted':inserted,'failed':failed}),flush=True)
    out={'expected':len(meetings),'pending_at_start':len(pending),'processed':processed,'inserted':inserted,'failed':failed}
    Path(report).write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out)); c.close()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--plan',required=True); p.add_argument('--database',required=True); p.add_argument('--registry',required=True); p.add_argument('--archive',required=True); p.add_argument('--run',required=True); p.add_argument('--report',required=True); p.add_argument('--workers',type=int,default=4)
    a=p.parse_args(); main(a.plan,a.database,a.registry,a.archive,a.run,a.report,a.workers)
