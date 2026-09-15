"""Build a read-only, source-linked spot check from the saved trials database."""
import argparse
import html
import json
import sqlite3
from pathlib import Path
from .trial_calendar_expansion import track_key

HORSES=['Autumn Glow','Sheza Alibi','Joliestar','Fangirl','Lady Shenandoah','Giga Kick','Ole Dancer','Sir Delius']


def build(database,output,start='2026-07-13',end='2026-09-12'):
    db=sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    cards=[];total=0
    for name in HORSES:
        horse=db.execute('SELECT horse_id FROM horses WHERE canonical_name=? COLLATE NOCASE',(name,)).fetchone()
        events={}
        if horse:
            for row in db.execute('SELECT * FROM trial_calendar_observations WHERE horse_id=? AND event_date BETWEEN ? AND ? ORDER BY observed_at',(horse[0],start,end)):
                raw=json.loads(row['detail_json']); key=(row['event_date'],track_key(row['track']),row['heat_number'],row['event_type'])
                events[key]={'date':row['event_date'],'track':row['track'],'heat':row['heat_number'],'kind':row['event_type'],
                    'finish':row['finish_position'],'field':row['field_size'],'listed':row['listed_runners'],
                    'distance':row['distance_metres'],'margin':raw.get('beaten_margin'),'jockey':raw.get('jockey_name'),
                    'clock':raw['detail'].get('heat_time_seconds'),'url':row['source_url'],'status':row['review_status'],
                    'going':raw.get('going'),'observed':row['observed_at'],'source':'Racing.com structured results'}
            for row in db.execute('SELECT * FROM trial_history_observations WHERE horse_id=? AND event_date BETWEEN ? AND ?',(horse[0],start,end)):
                raw=json.loads(row['detail_json'])
                # Prefer complete structured fields; profile-only observations remain visible.
                profile_track={'RAND':'randwick','RHIL':'rosehill','W FM':'warwickfarm'}.get(raw['track_label'],track_key(raw['track_label']))
                matches=[e for e in events.values() if e['date']==row['event_date'] and e['heat']==row['heat_number'] and e['kind']=='official_trial' and track_key(e['track'])==profile_track]
                if matches:
                    e=matches[0]
                    if e['field'] is None and e['finish']==row['finish_position']:
                        e['field']=row['field_size']
                        e['source']+='; starter count corroborated by Racing NSW history'
                        e['secondary_url']=row['meeting_url']+'#Race'+str(row['heat_number'])
                    continue
                key=(row['event_date'],raw['track_label'],row['heat_number'],'official_trial')
                events[key]={'date':row['event_date'],'track':raw['track_label'],'heat':row['heat_number'],'kind':'official_trial',
                    'finish':row['finish_position'],'field':row['field_size'],'listed':row['field_size'],'distance':None,
                    'margin':None,'jockey':None,'clock':None,'url':row['meeting_url']+'#Race'+str(row['heat_number']),
                    'status':'profile_history_only','going':None,'observed':row['observed_at'],'source':'Racing NSW horse history','text':raw['source_text']}
        total+=len(events);items=[]
        for e in sorted(events.values(),key=lambda e:(e['date'],e['heat']),reverse=True):
            finish=str(e['finish']) if e['finish'] is not None else 'Unclassified'
            result=finish+' / '+str(e['field']) if e['field'] else finish+' · field unconfirmed'
            status={'verified_result':'Accepted source result','corroborates_existing_event':'Matches stored meeting position and distance','profile_history_only':'Profile history — full meeting pending'}.get(e['status'],'Held for review: '+e['status'].replace('_',' '))
            facts=[f"{e['distance']}m" if e['distance'] else None,e['going'],e['jockey'],f"Margin: {e['margin']}L" if e['margin'] is not None else None,f"Heat time: {e['clock']:.2f}s" if e['clock'] else None]
            text=' · '.join(str(f) for f in facts if f) or e.get('text','')
            secondary=f'<a href="{html.escape(e["secondary_url"],quote=True)}" target="_blank" rel="noopener"> · Racing NSW cross-check ↗</a>' if e.get('secondary_url') else ''
            items.append(f'''<article><div class="line"><strong>{e['date']} · {html.escape(e['track'])} · Heat {e['heat']}</strong><b>{html.escape(result)}</b></div><p class="kind">{'Jumpout' if e['kind']=='jumpout' else 'Official trial'} · {html.escape(status)}</p><p>{html.escape(text)}</p><a href="{html.escape(e['url'],quote=True)}" target="_blank" rel="noopener">Check official result ↗</a>{secondary}<small>{e['source']} · collected {e['observed'][:10]} · {e['listed']} listed runners</small></article>''')
        if not events:items=['<div class="missing"><strong>No stored result in this window.</strong><p>This is not proof that the horse did not trial. Coverage exceptions remain under review.</p></div>']
        cards.append(f'<section data-name="{name.lower()}"><div class="line"><h2>{name}</h2><span>{len(events)} records</span></div>'+''.join(items)+'</section>')
    db.close()
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Star horses · Trial review</title><style>*{box-sizing:border-box}body{margin:0;background:#f1f4f7;color:#192735;font:16px/1.55 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:30px 20px}header{background:#132d39;color:white;padding:28px;border-radius:16px}h1{font-size:32px;line-height:1.2}h2{font-size:24px;margin:0}.eyebrow{color:#9fdbcd;text-transform:uppercase;letter-spacing:.1em;font-size:12px}.notice{background:#fff0cb;border-left:4px solid #be8610;padding:16px;margin:20px 0}input{width:100%;font:inherit;padding:13px 16px;border:1px solid #b9c8d0;border-radius:8px;margin:8px 0 20px}section{background:white;border:1px solid #d9e2e8;border-radius:12px;padding:24px;margin-bottom:20px}.line{display:flex;justify-content:space-between;gap:16px;align-items:baseline}.line b{white-space:nowrap}article{border-top:1px solid #e2e8ec;margin-top:18px;padding-top:18px}article p{margin:8px 0}.kind{color:#18705b;font-size:14px}small{display:block;color:#667482;margin-top:8px}.missing{background:#fff7e8;padding:16px;margin-top:18px}a{color:#126983}footer{font-size:14px;color:#667482}@media(max-width:600px){main{padding:16px 12px}header,section{padding:18px}.line{display:block}.line b{display:block;margin-top:5px}}</style><main><header><div class="eyebrow">BetMate · Source-linked database check</div><h1>Star horses: trials & jumpouts</h1><p>START to END · NSW, Victoria and ACT · completed days</p><strong>8 horses · TOTAL stored records</strong></header><div class="notice"><strong>Expanded coverage:</strong> every day in this window was checked for trial and jumpout meetings. Empty source meetings, ambiguous heats and unmatched horses remain explicit review items. A listed runner count is not necessarily a starter count. Times below are heat times, not each horse’s individual time.</div><label for="search">Find a horse</label><input id="search" type="search" placeholder="Autumn Glow, Sheza Alibi…">CARDS<footer>Read-only snapshot of the local review database. Trials and jumpouts are labelled separately. Some source pages may require cookies or JavaScript. This page shows stored evidence, not a fitness rating.</footer></main><script>document.querySelector('#search').addEventListener('input',e=>{let q=e.target.value.toLowerCase().trim();document.querySelectorAll('section').forEach(s=>s.hidden=!s.dataset.name.includes(q))})</script></html>'''
    output.mkdir(parents=True,exist_ok=True)
    (output/'index.html').write_text(page.replace('START',start).replace('END',end).replace('TOTAL',str(total)).replace('CARDS',''.join(cards)))
    return {'horses':len(HORSES),'records':total}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.database,a.output)))
