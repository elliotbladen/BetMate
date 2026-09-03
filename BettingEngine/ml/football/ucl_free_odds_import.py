"""Import the free Kaggle UCL 1X2 file as unverified closing benchmarks."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/ucl/markets/ucl_free_unverified_1x2.csv"
REPORT = ROOT / "ml/football/reports/ucl_free_odds_import.json"

def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")

def run(source: Path) -> dict:
    frame = pd.read_csv(source, encoding="utf-8-sig")
    league = frame["Championat"].astype(str).str.lower()
    frame = frame[league.eq("europe/champions-league")].copy()
    rename = {"Saison":"season_source", "Date":"match_date", "Heure":"kickoff_source", "Équipe Domicile":"home_name", "Équipe Extérieure":"away_name", "Equipe Domicile":"home_name", "Equipe Extérieure":"away_name", "Score Domicile":"home_goals", "Score Extérieur":"away_goals", "Cote 1":"home_odds", "Cote X":"draw_odds", "Cote 2":"away_odds"}
    frame = frame.rename(columns=rename)
    # Handle mojibake column names emitted by the downloaded CSV.
    for col, target in [(c, "home_name") for c in frame.columns if "Domicile" in c and "quipe" in c]: frame = frame.rename(columns={col: target})
    for col, target in [(c, "away_name") for c in frame.columns if "Ext" in c and "quipe" in c]: frame = frame.rename(columns={col: target})
    frame["home_club_id"] = frame["home_name"].map(slug); frame["away_club_id"] = frame["away_name"].map(slug)
    frame["source"] = "kaggle_rayeenjlassi"; frame["closing_status"] = "unverified_static_close"; frame["market_type"] = "h2h"
    frame["quote_id"] = "kaggle-ucl-" + frame.index.astype(str); frame["market_id"] = frame["quote_id"]
    keep = ["quote_id","market_id","season_source","match_date","kickoff_source","home_name","away_name","home_club_id","away_club_id","home_goals","away_goals","home_odds","draw_odds","away_odds","source","closing_status","market_type"]
    missing = [c for c in keep if c not in frame.columns]
    if missing: raise ValueError(f"odds file missing fields after normalization: {', '.join(missing)}")
    OUT.parent.mkdir(parents=True, exist_ok=True); frame[keep].to_csv(OUT, index=False)
    result = {"status":"ucl_free_odds_imported_unverified", "rows":len(frame), "seasons":sorted(frame.season_source.astype(str).unique().tolist()), "source":"Kaggle", "closing_status":"unverified_static_close", "timestamps_present":False, "output":str(OUT.relative_to(ROOT))}
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8"); return result

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--source", type=Path, required=True); print(json.dumps(run(parser.parse_args().source), indent=2))
if __name__ == "__main__": main()
