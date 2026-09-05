"""Build the local Chelmsford Stakes shadow map demo from the current card."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from racing_engine.map_position import RunnerInput, predict_field
from racing_engine.storage import RacingStore

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "data" / "racing" / "chelmsford-map-2026.json"
CARD = [
 (1,"Ceolwulf",8,"Chad Schofield","Joseph Pride",59.0,"x66x5"),
 (2,"Lindermann",9,"Nash Rawiller","Chris Waller",59.0,"922x9"),
 (3,"Campaldino",10,"Tim Clark","Gai Waterhouse & Adrian Bott",59.0,"5172x"),
 (4,"Soul Of Spain",7,"Zac Lloyd","Chris Waller",59.0,"262x6"),
 (5,"The Euphrates",4,"Regan Bayliss","Gai Waterhouse & Adrian Bott",59.0,"2417x"),
 (6,"Travolta",2,"Tommy Berry","Chris Waller",59.0,"434x9"),
 (7,"Green Spaces",1,"Rachel King","Bjorn Baker",58.5,"621x8"),
 (9,"Fangirl",6,"James McDonald","Chris Waller",57.0,"834x0"),
 (10,"Piggyback",5,"Adam Hyeronimus","Ciaron Maher",57.0,"456x5"),
]

def main() -> None:
    store=RacingStore(ROOT/"data"/"racing_engine.sqlite"); as_of=datetime.now(timezone.utc).isoformat()
    try:
        predicted=predict_field(store,source="racing-nsw-card",race_date="2026-09-05",track_slug="randwick",race_number=9,
          runners=[RunnerInput(number=n,name=name,barrier=barrier) for n,name,barrier,*_ in CARD],as_of=as_of)
    finally: store.close()
    card_by_number={row[0]:row for row in CARD}; runners=[]
    for prediction in predicted:
        n,name,barrier,jockey,trainer,weight,form=card_by_number[prediction["runner_number"]]
        runners.append({**prediction,"jockey":jockey,"trainer":trainer,"weight":weight,"form":form})
    payload={"meeting":"Royal Randwick","raceNumber":9,"raceName":"Asahi Super Dry Chelmsford Stakes",
      "distance":1600,"class":"Group 2 · Weight For Age","startTime":"4:35 PM","trackCondition":"Soft 5",
      "rail":"+3m entire course","weather":"Fine","modelVersion":"map-position-shadow-v1",
      "status":"SHADOW — V1 FAILED BASELINE; VISUAL RESEARCH ONLY","asOf":as_of,
      "scratched":[{"number":8,"name":"Attica","barrier":3}],"runners":runners,
      "sources":["Racing NSW current scratchings/conditions","Published final field","BetMate three-year sectional history"]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True); OUTPUT.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(OUTPUT)

if __name__=="__main__": main()
