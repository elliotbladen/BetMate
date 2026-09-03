from pathlib import Path
import pandas as pd
from difflib import SequenceMatcher
from .ucl_market_backtest import team_key

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/ucl/matches/ucl_matches_openfootball_repaired.csv"
ODDS = ROOT / "data/ucl/markets/ucl_betexplorer_2024_25_1x2.csv"
OUT = ROOT / "data/ucl/matches/ucl_matches_openfootball_repaired_2425.csv"
MAP = ROOT / "data/ucl/markets/ucl_betexplorer_match_mapping_2024_25.csv"

def run():
    m = pd.read_csv(SOURCE)
    o = pd.read_csv(ODDS)
    cur = m[m.season.eq("2024-25")].copy()
    cur["hk"] = cur.home_club_id.map(team_key); cur["ak"] = cur.away_club_id.map(team_key)
    o["hk"] = o.home_slug.map(team_key); o["ak"] = o.away_slug.map(team_key)
    known = set(o.hk) | set(o.ak)
    def resolve(value):
        key = team_key(value)
        ranked = sorted((SequenceMatcher(None, key, k).ratio(), k) for k in known)
        return ranked[-1][1] if ranked and ranked[-1][0] >= .45 else key
    cur["hk"] = cur.hk.map(resolve); cur["ak"] = cur.ak.map(resolve)
    cur["n"] = cur.groupby(["hk", "ak"]).cumcount(); o["n"] = o.groupby(["hk", "ak"]).cumcount()
    lookup = o[["hk", "ak", "n", "date", "home_slug", "away_slug", "home_odds", "draw_odds", "away_odds"]]
    r = cur.merge(lookup, on=["hk", "ak", "n"], how="left")
    r["kickoff_utc"] = pd.to_datetime(r.date, dayfirst=True, errors="coerce", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    m = m.set_index("match_id"); r = r.set_index("match_id"); m.loc[r.index, "kickoff_utc"] = r.kickoff_utc
    m.reset_index().to_csv(OUT, index=False)
    r.reset_index()[["match_id", "date", "home_slug", "away_slug", "home_odds", "draw_odds", "away_odds"]].to_csv(MAP, index=False)
    print({"rows":len(cur), "dates_repaired":int(r.kickoff_utc.notna().sum()), "output":str(OUT)})
if __name__ == "__main__": run()
