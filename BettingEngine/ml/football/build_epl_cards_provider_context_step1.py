"""Turn FotMob match context into leak-free prior rolling team features."""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "epl"
BASE = DATA / "cards" / "epl_cards_context_features_2022_23_to_2025_26.csv"
PROVIDER = DATA / "context" / "fotmob_epl_match_context_2022_23_to_2025_26.csv"
OUT = DATA / "cards" / "epl_cards_context_features_step1_enriched.csv"
REPORT = ROOT / "reports" / "epl_cards_step1_provider_audit.md"
ROLL = 10


def numeric_crosses(value):
    if pd.isna(value):
        return np.nan
    try:
        return float(str(value).split(" ", 1)[0])
    except (TypeError, ValueError):
        return np.nan


def main() -> None:
    base = pd.read_csv(BASE)
    base["Date"] = pd.to_datetime(base["Date"], format="mixed")
    p = pd.read_csv(PROVIDER)
    p["date"] = pd.to_datetime(p["date"])
    for side in ("home", "away"):
        p[f"{side}_accurate_crosses_n"] = p[f"{side}_accurate_crosses"].map(numeric_crosses)

    numeric = ["blocked_shots", "accurate_crosses_n", "shots_inside_box", "touches_opp_box", "possession", "shots", "shots_on_target", "starter_rating_mean", "starter_count"]
    states = defaultdict(lambda: defaultdict(lambda: deque(maxlen=ROLL)))
    rows = []
    for _, m in p.sort_values(["date", "home_team", "away_team"]).iterrows():
        rec = {"Season": m.season, "Date": m.date, "HomeTeam": m.home_team, "AwayTeam": m.away_team}
        for side in ("home", "away"):
            team = m[f"{side}_team"]
            for metric in numeric:
                q = states[team][metric]
                rec[f"{side}_{metric}_prior"] = float(np.mean(q)) if q else np.nan
            rec[f"{side}_provider_prior_matches"] = len(states[team]["shots"])
        rows.append(rec)
        for side, opp in (("home", "away"), ("away", "home")):
            team = m[f"{side}_team"]
            for metric in numeric:
                value = m.get(f"{side}_{metric}") if metric != "accurate_crosses_n" else m.get(f"{side}_accurate_crosses_n")
                if pd.notna(value):
                    states[team][metric].append(float(value))

    provider = pd.DataFrame(rows)
    keys = ["Season", "Date", "HomeTeam", "AwayTeam"]
    out = base.merge(provider, on=keys, how="left", validate="one_to_one")
    out.to_csv(OUT, index=False)
    feature_cols = [c for c in out if c.endswith("_prior")]
    cov = out.groupby("Season")[feature_cols].apply(lambda x: x.notna().mean()).round(3)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("# EPL cards provider context audit\n\nRows: %d\n\nProvider outcomes are updated only after each fixture; all *_prior fields are strictly pre-match.\n\n" % len(out) + cov.to_string() + "\n")
    print(f"Saved {len(out)} rows to {OUT}")
    print(cov)


if __name__ == "__main__":
    main()
