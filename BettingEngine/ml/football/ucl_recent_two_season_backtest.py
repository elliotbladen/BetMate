"""Backtest the current UCL stack against the two most recent seasons' prices."""
from pathlib import Path
import json
import pandas as pd
from .ucl_backtest import multiclass_metrics

ROOT = Path(__file__).resolve().parents[2]
PRED = ROOT / "data/ucl/clv/ucl_shared_walk_forward_predictions.csv"
MARKETS = {
    "2024-25": ROOT / "data/ucl/markets/ucl_betexplorer_backtest_2024_25_date_safe.csv",
    "2025-26": ROOT / "data/ucl/markets/ucl_footiqo_backtest_2025_26_date_safe.csv",
}
OUT = ROOT / "data/ucl/markets/ucl_recent_two_season_stack_backtest.csv"
REPORT = ROOT / "ml/football/reports/ucl_recent_two_season_stack_backtest.json"

def run():
    pred = pd.read_csv(PRED); pred = pred[pred.season.astype(str).isin(MARKETS)].copy()
    rows = []
    for season, path in MARKETS.items():
        m = pd.read_csv(path); m = m[m.season.astype(str) == season].copy()
        x = m.merge(pred[["match_id", "p_home", "p_draw", "p_away"]], on="match_id", suffixes=("_market", ""))
        for _, r in x.iterrows():
            odds = [r.get("home_odds", r.get("xbetClose1FT")), r.get("draw_odds", r.get("xbetCloseXFT")), r.get("away_odds", r.get("xbetClose2FT"))]
            if any(pd.isna(v) or float(v) <= 1 for v in odds): continue
            q = [1 / float(v) for v in odds]; z = sum(q); q = [v / z for v in q]
            probs = [float(r.p_home), float(r.p_draw), float(r.p_away)]
            edges = [probs[i] / q[i] - 1 for i in range(3)]; i = max(range(3), key=lambda j: edges[j])
            actual = "H" if r.home_goals > r.away_goals else ("A" if r.home_goals < r.away_goals else "D")
            rows.append({"season":season,"match_id":r.match_id,"home_team":r.home_team,"away_team":r.away_team,"p_home":probs[0],"p_draw":probs[1],"p_away":probs[2],"edge":edges[i],"bet":["H","D","A"][i],"actual":actual,"odds":float(odds[i]),"profit":float(odds[i])-1 if ["H","D","A"][i] == actual else -1})
    out = pd.DataFrame(rows); OUT.parent.mkdir(parents=True, exist_ok=True); out.to_csv(OUT, index=False)
    summary = {"games_with_closing_prices":len(out), "seasons":{}}
    for season in MARKETS:
        s = out[out.season == season]; summary["seasons"][season] = {}
        for threshold in (0.10, 0.20):
            b = s[s.edge >= threshold]; summary["seasons"][season][f"edge_{int(threshold*100)}pct"] = {"bets":len(b),"wins":int((b.profit > 0).sum()),"profit":round(float(b.profit.sum()),2),"roi":round(float(b.profit.sum()/len(b)*100),2) if len(b) else None}
    for threshold in (0.10, 0.20):
        b = out[out.edge >= threshold]; summary[f"combined_edge_{int(threshold*100)}pct"] = {"bets":len(b),"wins":int((b.profit > 0).sum()),"profit":round(float(b.profit.sum()),2),"roi":round(float(b.profit.sum()/len(b)*100),2) if len(b) else None}
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8"); return summary

if __name__ == "__main__": print(json.dumps(run(), indent=2))
