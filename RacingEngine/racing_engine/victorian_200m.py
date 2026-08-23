"""Acquire Racing.com's official runner-level Victorian 200m CSV sectionals."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from .horse_identity import clean_name
from .racing_com import PUBLIC_CLIENT_KEY
from .storage import RacingStore,utc_now

ROOT=Path(__file__).resolve().parents[1]
VERSION="racing-com-vic-200m-v1"
BASE="https://d3qmfyv6ad9vwv.cloudfront.net"
GRAPHQL="https://graphql.rmdprod.racing.com"

def _seconds(value:str)->float:
 minutes,seconds=value.split(":",1);return int(minutes)*60+float(seconds)

def parse_csv(payload:bytes,distance_metres:int)->list[dict]:
 text=payload.decode("utf-8-sig",errors="replace")
 if "no-content" in text.lower() or ";" not in text:return []
 rows=list(csv.reader(io.StringIO(text),delimiter=";"));result=[]
 for row in rows[1:]:
  if len(row)<5 or not row[0].strip():continue
  try:runner_number=int(row[1])
  except ValueError:continue
  points=[]
  for index in range(2,len(row)-2,3):
   try:
    completed=int(row[index]);speed=float(row[index+1]);duration=_seconds(row[index+2])
   except (ValueError,IndexError):continue
   if completed<=0 or completed>distance_metres or duration<=0:continue
   points.append({"completed_metres":completed,"marker_metres":distance_metres-completed,
    "speed_mps":speed,"section_seconds":duration})
  if points:result.append({"horse_name":row[0].strip(),"runner_number":runner_number,"points":points})
 return result

def parse_graphql(payload:bytes,distance_metres:int)->list[dict]:
 try:data=json.loads(payload)["data"]["getRaceForm"]["raceEntryTimes"] or []
 except (KeyError,TypeError,ValueError):return []
 result=[]
 for runner in data:
  points=[]
  for split in runner.get("splitTimes") or []:
   label=str(split.get("distance") or "").upper();parts=label.split("-")
   if len(parts)!=2:continue
   def metres(token):return 0 if token=="FINISH" else int(re.sub(r"\D","",token) or 0)
   start,end=metres(parts[0]),metres(parts[1]);segment=abs(start-end)
   try:duration=float(split["time"]);speed=float(split["avgSpeed"])
   except (KeyError,TypeError,ValueError):continue
   if segment<=0 or duration<=0:continue
   points.append({"completed_metres":distance_metres-end,"marker_metres":end,"speed_mps":speed,
    "section_seconds":duration,"position":split.get("position")})
  if points:result.append({"horse_name":runner.get("horseName") or "","runner_number":int(runner["saddleNumber"]),"points":points})
 return result

def _download(url:str)->bytes:
 request=Request(url,headers={"User-Agent":"Mozilla/5.0 RacingEngine research importer"})
 with urlopen(request,timeout=30) as response:return response.read()

def _download_graphql(meet_code:str,race_number:int)->tuple[bytes,str]:
 query='''{getRaceForm(meetCode:"%s",raceNumber:%d){raceEntryTimes{horseName saddleNumber splitTimes{distance position time avgSpeed}}}}'''%(meet_code,race_number)
 url=GRAPHQL+"?"+urlencode({"query":query});request=Request(url,headers={"X-Api-Key":PUBLIC_CLIENT_KEY,"User-Agent":"Mozilla/5.0 RacingEngine research importer"})
 with urlopen(request,timeout=30) as response:return response.read(),url

def schema(store:RacingStore)->None:
 store.connection.executescript("""CREATE TABLE IF NOT EXISTS v2_vic_200m_sectionals(
 version TEXT NOT NULL,race_id TEXT NOT NULL,runner_number INTEGER NOT NULL,horse_key TEXT NOT NULL,
 marker_metres INTEGER NOT NULL,completed_metres INTEGER NOT NULL,section_seconds REAL NOT NULL,speed_mps REAL,
 finish_position_csv INTEGER,source_url TEXT NOT NULL,payload_sha256 TEXT NOT NULL,created_at TEXT NOT NULL,
 PRIMARY KEY(version,race_id,runner_number,marker_metres));
 CREATE TABLE IF NOT EXISTS v2_vic_200m_acquisition_audit(
 version TEXT NOT NULL,race_id TEXT NOT NULL,status TEXT NOT NULL,source_url TEXT NOT NULL,rows_parsed INTEGER NOT NULL,
 rows_matched INTEGER NOT NULL,detail_json TEXT NOT NULL,checked_at TEXT NOT NULL,PRIMARY KEY(version,race_id));""")
 columns={row[1] for row in store.connection.execute("PRAGMA table_info(v2_vic_200m_sectionals)")}
 if "position_at_marker" not in columns:store.connection.execute("ALTER TABLE v2_vic_200m_sectionals ADD COLUMN position_at_marker INTEGER")

def acquire(store:RacingStore,from_date:str|None=None,to_date:str|None=None,refresh:bool=False)->dict:
 schema(store);params=[];where="r.source='racing-com-rv-authorised'"
 if from_date:where+=" AND r.race_date>=?";params.append(from_date)
 if to_date:where+=" AND r.race_date<=?";params.append(to_date)
 races=store.connection.execute(f"""SELECT r.*,json_extract(r.raw_json,'$.meet.id') meet_code FROM race_results r
  WHERE {where} ORDER BY r.race_date,r.track_slug,r.race_number""",params).fetchall()
 totals={"races_considered":len(races),"available":0,"unavailable":0,"matched_runners":0,"ambiguous_or_unmatched":0,"segments":0}
 now=utc_now()
 for race in races:
  race_id=f"{race['race_date']}|{race['track_slug']}|{race['race_number']}"
  existing=store.connection.execute("SELECT status FROM v2_vic_200m_acquisition_audit WHERE version=? AND race_id=?",(VERSION,race_id)).fetchone()
  if existing and not refresh:totals["available" if existing[0]=="available" else "unavailable"]+=1;continue
  csv_url=f"{BASE}/{race['meet_code']}_{int(race['race_number']):02d}.csv";url=csv_url
  error=None
  try:
   payload,url=_download_graphql(str(race['meet_code']),int(race['race_number']));parsed=parse_graphql(payload,int(race['distance_metres'] or 0))
   if not parsed:payload=_download(csv_url);url=csv_url;parsed=parse_csv(payload,int(race['distance_metres'] or 0))
  except Exception as exc:payload=b"";parsed=[];error=str(exc)
  official=store.connection.execute("SELECT runner_number,horse_key,horse_name,finish_position FROM v2_clean_runner_results WHERE race_id=?",(race_id,)).fetchall()
  by_name={clean_name(race["source"],x["horse_name"])[0].casefold():x for x in official};matched=0;unmatched=[]
  store.connection.execute("DELETE FROM v2_vic_200m_sectionals WHERE version=? AND race_id=?",(VERSION,race_id))
  digest=hashlib.sha256(payload).hexdigest()
  for item in parsed:
   key=clean_name(race["source"],item["horse_name"])[0].casefold();runner=by_name.get(key)
   if runner is None or int(runner["runner_number"])!=item["runner_number"]:unmatched.append(item["horse_name"]);continue
   matched+=1
   for point in item["points"]:
    store.connection.execute("""INSERT INTO v2_vic_200m_sectionals(version,race_id,runner_number,horse_key,marker_metres,completed_metres,
     section_seconds,speed_mps,finish_position_csv,source_url,payload_sha256,created_at,position_at_marker) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
     (VERSION,race_id,runner["runner_number"],runner["horse_key"],point["marker_metres"],point["completed_metres"],point["section_seconds"],point["speed_mps"],runner["finish_position"],url,digest,now,point.get("position")));totals["segments"]+=1
  status="available" if parsed and matched else "unavailable";totals[status]+=1;totals["matched_runners"]+=matched;totals["ambiguous_or_unmatched"]+=len(unmatched)
  detail={"parsed_runners":len(parsed),"unmatched_names":unmatched,"error":error if not parsed else None,"official_identity_owner":"v2_clean_runner_results"}
  store.connection.execute("INSERT OR REPLACE INTO v2_vic_200m_acquisition_audit VALUES(?,?,?,?,?,?,?,?)",(VERSION,race_id,status,url,len(parsed),matched,json.dumps(detail,sort_keys=True),now));store.connection.commit()
 return {"version":VERSION,**totals,"accepted_rating_changed":False}

def main():
 p=argparse.ArgumentParser();p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite");p.add_argument("--from-date");p.add_argument("--to-date");p.add_argument("--refresh",action="store_true");p.add_argument("--output",type=Path);a=p.parse_args();store=RacingStore(a.database)
 try:result=acquire(store,a.from_date,a.to_date,a.refresh)
 finally:store.close()
 rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered)
 print(rendered,end="")
if __name__=="__main__":main()
