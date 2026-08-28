"""Locked ratings-only Sydney/Melbourne Group 1 Betfair close backtest."""
from __future__ import annotations

import argparse,json,random,statistics
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

from .achieved_run_breakout import ROOT
from .betfair_anz import relevant_rows
from .collateral_revision_v2 import MODEL_VERSION as RUN_MODEL_VERSION
from .evaluation_protocol import load_protocol
from .horse_ability_suitability_v2 import build_raw_examples
from .horse_ability_v2 import probabilities,utc_now
from .storage import RacingStore

MODEL_VERSION="group1-betfair-close-v1.0-locked"
ABILITY_VERSION="horse-ability-v2.8-final-research-freeze"
START_DATE="2025-08-23";END_DATE="2026-08-22";AVAILABLE_END="2026-07-31"
TEMPERATURE=60.0;BOOK_PERCENTAGE=1.10;MIN_EDGE=0.10;STAKE=1.0
COMMISSION={"NSW":0.10,"VIC":0.07}


def model_quote(probability:float)->float:
    return 1.0/(probability*BOOK_PERCENTAGE)


def qualifies(close_price:float,quote:float)->bool:
    return close_price/quote-1.0>MIN_EDGE+1e-12


def settle_market(bets:list[dict[str,Any]],commission_rate:float)->tuple[float,float]:
    gross=sum((bet["close_price"]-1.0)*STAKE if bet["won"] else -STAKE for bet in bets)
    net=gross-(max(0.0,gross)*commission_rate)
    return gross,net


def roi_interval(races:list[dict[str,Any]],repetitions:int=10000)->dict[str,float|int|None]:
    eligible=[race for race in races if race["bet_count"]]
    if not eligible:return {"lower":None,"upper":None,"repetitions":repetitions,"seed":20260828}
    rng=random.Random(20260828);values=[]
    for _ in range(repetitions):
        sample=[eligible[rng.randrange(len(eligible))] for _ in eligible]
        stake=sum(race["bet_count"]*STAKE for race in sample)
        values.append(sum(race["net_pnl"] for race in sample)/stake)
    values.sort();return {"lower":values[int(.025*repetitions)],"upper":values[int(.975*repetitions)-1],
                          "repetitions":repetitions,"seed":20260828}


def _schema(store:RacingStore)->None:
    store.connection.executescript("""CREATE TABLE IF NOT EXISTS group1_backtest_bets (
      version TEXT NOT NULL,race_id TEXT NOT NULL,runner_number INTEGER NOT NULL,horse_key TEXT NOT NULL,
      horse_name TEXT NOT NULL,ability_rating REAL NOT NULL,model_probability REAL NOT NULL,
      model_price_110 REAL NOT NULL,betfair_close REAL NOT NULL,edge REAL NOT NULL,won INTEGER NOT NULL,
      stake REAL NOT NULL,gross_pnl REAL NOT NULL,state TEXT NOT NULL,detail_json TEXT NOT NULL,
      PRIMARY KEY(version,race_id,runner_number));""")


def run(store:RacingStore,raw_root:Path,protocol_path:Path)->dict[str,Any]:
    protocol=load_protocol(protocol_path);examples,_,_=build_raw_examples(store,protocol)
    group1={race["race_id"]:race for race in examples if START_DATE<=race["race_date"]<=END_DATE and
        race["class_family"]=="group_1" and race["state"] in ("NSW","VIC")}
    market=defaultdict(list)
    for row in relevant_rows(raw_root,START_DATE,min(END_DATE,AVAILABLE_END)):
        market[(row["race_date"],row["track_slug"],row["race_number"])].append(row)
    _schema(store);store.connection.execute("DELETE FROM group1_backtest_bets WHERE version=?",(MODEL_VERSION,))
    race_reports=[];all_bets=[];exclusions=Counter()
    for race_id,race in sorted(group1.items(),key=lambda item:item[1]["race_date"]):
        if race["race_date"]>AVAILABLE_END:
            exclusions["betfair_month_not_published"]+=1;continue
        prices=market.get((race["race_date"],race["track_slug"],race["race_number"]),[])
        if not prices:exclusions["market_not_matched"]+=1;continue
        by_number={row["runner_number"]:row for row in prices};matched=[]
        for runner in race["runners"]:
            price=by_number.get(runner["runner_number"])
            if not price or price["close_price"] is None:continue
            if price["horse_key"]!=runner["horse_key"]:continue
            matched.append((runner,price))
        if len(matched)!=len(race["runners"]):
            exclusions["incomplete_runner_match"]+=1;continue
        probs=probabilities([runner["base"] for runner,_ in matched],TEMPERATURE);bets=[]
        quoted=[]
        for (runner,price),prob in zip(matched,probs):
            quote=model_quote(prob);edge=price["close_price"]/quote-1.0
            quoted.append({"runner_number":runner["runner_number"],"horse_name":runner["horse_name"],
                "rating":runner["base"],"probability":prob,"model_price_110":quote,
                "betfair_close":price["close_price"],"edge":edge})
            if qualifies(price["close_price"],quote):
                bet={**quoted[-1],"horse_key":runner["horse_key"],"won":runner["finish_position"]==1,
                     "close_price":price["close_price"],"state":race["state"],"race_id":race_id}
                bets.append(bet);all_bets.append(bet)
        gross,net=settle_market(bets,COMMISSION[race["state"]])
        for bet in bets:
            individual=(bet["close_price"]-1)*STAKE if bet["won"] else -STAKE
            store.connection.execute("INSERT INTO group1_backtest_bets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (MODEL_VERSION,race_id,bet["runner_number"],bet["horse_key"],bet["horse_name"],bet["rating"],
                 bet["probability"],bet["model_price_110"],bet["close_price"],bet["edge"],int(bet["won"]),
                 STAKE,individual,race["state"],json.dumps({"commission_rate":COMMISSION[race["state"]]},sort_keys=True)))
        race_reports.append({"race_id":race_id,"race_date":race["race_date"],"state":race["state"],
            "track_slug":race["track_slug"],"race_number":race["race_number"],"runners":len(matched),
            "bets":bets,"bet_count":len(bets),"gross_pnl":gross,"net_pnl":net})
    store.connection.commit();stake=len(all_bets)*STAKE
    gross=sum(row["gross_pnl"] for row in race_reports);net=sum(row["net_pnl"] for row in race_reports)
    cumulative=0.0;peak=0.0;max_drawdown=0.0
    for race in race_reports:
        cumulative+=race["net_pnl"];peak=max(peak,cumulative);max_drawdown=max(max_drawdown,peak-cumulative)
    by_state={}
    for state in ("NSW","VIC"):
        rows=[race for race in race_reports if race["state"]==state];state_stake=sum(race["bet_count"] for race in rows)*STAKE
        state_net=sum(race["net_pnl"] for race in rows)
        by_state[state]={"races":len(rows),"bets":int(state_stake/STAKE),"stake":state_stake,"net_pnl":state_net,
                         "net_roi":state_net/state_stake if state_stake else None}
    return {"report_name":"one-year Sydney/Melbourne Group 1 ratings-only Betfair close backtest",
        "version":MODEL_VERSION,"ability_version":ABILITY_VERSION,"period":{"requested_start":START_DATE,
            "requested_end":END_DATE,"betfair_available_end":AVAILABLE_END},"rules":{"model_book_percentage":BOOK_PERCENTAGE,
            "probability_temperature":TEMPERATURE,"minimum_quote_edge_strictly_greater_than":MIN_EDGE,
            "stake_per_selection":STAKE,"price":"BEST_AVAIL_BACK_AT_SCHEDULED_OFF",
            "edge_formula":"betfair_close / model_price_110 - 1","commission":COMMISSION,
            "commission_application":"state rate on positive net market profit after all bets in the race"},
        "coverage":{"group1_races_requested":len(group1),"races_tested":len(race_reports),"exclusions":dict(exclusions)},
        "result":{"bets":len(all_bets),"winning_bets":sum(bet["won"] for bet in all_bets),"stake":stake,
            "gross_pnl":gross,"gross_roi":gross/stake if stake else None,"net_pnl":net,
            "net_roi":net/stake if stake else None,"net_roi_race_bootstrap_95":roi_interval(race_reports),
            "maximum_drawdown":max_drawdown,"by_state":by_state},
        "races":race_reports,"generated_at":utc_now()}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--raw-root",type=Path,default=ROOT/"data"/"raw"/"betfair_anz")
    p.add_argument("--protocol",type=Path,default=ROOT/"config"/"evaluation_protocol_v1.json")
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"backtests"/"group1_betfair_close_v1.json")
    a=p.parse_args();store=RacingStore(a.database)
    try:report=run(store,a.raw_root,a.protocol)
    finally:store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
