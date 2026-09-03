"""Backtest UCL Over/Under 2.5 against Footiqo 2025/26 closing prices."""
from pathlib import Path
import numpy as np
import pandas as pd
from .ucl_shared_engine import load_matches, fit_before, price

ROOT = Path(__file__).resolve().parents[2]
PRED = ROOT / "data/ucl/clv/ucl_shared_walk_forward_predictions.csv"
ODDS = ROOT / "data/ucl/markets/ucl_footiqo_closing_1x2_2025_26.csv"
OUT = ROOT / "data/ucl/markets/ucl_footiqo_totals_backtest_2025_26.csv"

def run():
    p = pd.read_csv(PRED); p = p[p.season.eq("2025-26")].copy()
    odds = pd.read_csv(ODDS)
    # Footiqo rows are in the same fixture identity as the repaired calendar;
    # join by match_id through the repaired source order/mapping.
    mapping = pd.read_csv(ROOT / "data/ucl/markets/ucl_footiqo_match_mapping_2025_26.csv")
    p = p.merge(mapping[["match_id", "xbetCloseOver25", "xbetCloseUnder25"]], on="match_id", how="inner")
    matches = load_matches(); ratings = fit_before(matches, pd.Timestamp("2025-09-16", tz="UTC"))
    rows = []
    for _, r in p.iterrows():
        m = price(r.home_team, r.away_team, ratings)["scoreline_matrix"]
        over = float(sum(m[i, j] for i in range(m.shape[0]) for j in range(m.shape[1]) if i + j >= 3))
        rows.append((r.match_id, over, 1.0 - over))
    q = pd.DataFrame(rows, columns=["match_id", "model_over25", "model_under25"])
    j = p.merge(q, on="match_id");
    for c in ["xbetCloseOver25", "xbetCloseUnder25"]: j[c] = pd.to_numeric(j[c], errors="coerce")
    fair = 1 / j[["xbetCloseOver25", "xbetCloseUnder25"]].to_numpy(); fair /= fair.sum(1, keepdims=True)
    j["market_over25"], j["market_under25"] = fair[:,0], fair[:,1]
    j["edge_over25"] = j.model_over25 - j.market_over25; j["edge_under25"] = j.model_under25 - j.market_under25
    j["bet"] = np.where(j.edge_over25 >= j.edge_under25, "Over", "Under"); j["edge"] = j[["edge_over25", "edge_under25"]].max(axis=1)
    j["actual_over25"] = (j.home_goals + j.away_goals > 2.5).map({True:"Over", False:"Under"})
    j["odds"] = np.where(j.bet.eq("Over"), j.xbetCloseOver25, j.xbetCloseUnder25); j["profit"] = np.where(j.bet.eq(j.actual_over25), j.odds - 1, -1)
    j.to_csv(OUT, index=False); b = j[j.edge >= .10]
    return {"season":"2025-26", "matched":len(j), "edge_threshold":0.10, "bets":len(b), "wins":int((b.bet==b.actual_over25).sum()), "profit":round(float(b.profit.sum()),2), "roi":round(float(b.profit.mean()*100),2), "output":str(OUT)}

if __name__ == "__main__": print(run())
