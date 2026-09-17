"""Audit the EPL card-model data foundation before feature work begins."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
MATCHES = ROOT / "data" / "epl" / "matches" / "epl_matches.csv"
CARD_RESULTS = ROOT / "data" / "epl" / "cards" / "epl_card_results_2022_23_to_2025_26.csv"
CARD_ODDS = ROOT / "data" / "epl" / "cards" / "footiqo_epl_cards_closing_odds_2025_26.csv"
CARD_JOIN = ROOT / "data" / "epl" / "cards" / "epl_2025_26_card_market_join.csv"
REPORT = ROOT / "reports" / "epl_cards_step1_data_audit.json"


def main() -> None:
    df = pd.read_csv(MATCHES, low_memory=False)
    card_fields = ["HY", "AY", "HR", "AR"]
    market_fields = [
        c for c in df.columns
        if any(token in c.lower() for token in ("card", "booking", "o3.5", "u3.5"))
    ]
    required = ["Season", "Date", "HomeTeam", "AwayTeam", "Referee", "HY", "AY"]
    season = df.groupby("Season", dropna=False).agg(
        matches=("Date", "size"),
        referees=("Referee", lambda s: int(s.notna().sum())),
        home_yellows=("HY", lambda s: int(s.notna().sum())),
        away_yellows=("AY", lambda s: int(s.notna().sum())),
    )
    df["total_yellows"] = pd.to_numeric(df["HY"], errors="coerce") + pd.to_numeric(
        df["AY"], errors="coerce"
    )
    report = {
        "source": str(MATCHES.relative_to(ROOT.parent.parent)),
        "rows": int(len(df)),
        "date_min": str(df["Date"].min()),
        "date_max": str(df["Date"].max()),
        "seasons": int(df["Season"].nunique()),
        "required_fields_present": {c: c in df.columns for c in required},
        "field_coverage": {
            c: {"present": c in df.columns, "non_null": int(df[c].notna().sum()) if c in df else 0}
            for c in card_fields
        },
        "referees": {
            "unique": int(df["Referee"].nunique(dropna=True)),
            "missing": int(df["Referee"].isna().sum()),
        },
        "duplicate_fixture_keys": int(
            df.duplicated(["Date", "HomeTeam", "AwayTeam"], keep=False).sum()
        ),
        "yellow_card_target": {
            "mean": round(float(df["total_yellows"].mean()), 4),
            "over_3_5_rate": round(float((df["total_yellows"] > 3.5).mean()), 4),
            "missing": int(df["total_yellows"].isna().sum()),
        },
        "market_fields_found_in_match_file": market_fields,
        "normalized_card_results": {
            "path": str(CARD_RESULTS.relative_to(ROOT.parent.parent)),
            "exists": CARD_RESULTS.exists(),
            "rows": int(len(pd.read_csv(CARD_RESULTS))) if CARD_RESULTS.exists() else 0,
        },
        "yellow_card_closing_odds": {
            "path": str(CARD_ODDS.relative_to(ROOT.parent.parent)),
            "exists": CARD_ODDS.exists(),
            "rows": int(len(pd.read_csv(CARD_ODDS))) if CARD_ODDS.exists() else 0,
        },
        "yellow_card_market_join": {
            "path": str(CARD_JOIN.relative_to(ROOT.parent.parent)),
            "exists": CARD_JOIN.exists(),
            "rows": int(len(pd.read_csv(CARD_JOIN))) if CARD_JOIN.exists() else 0,
            "outcome_mismatches": int((~pd.read_csv(CARD_JOIN)["yellow_total_match"]).sum())
            if CARD_JOIN.exists() else 0,
        },
        "season_coverage": season.reset_index().to_dict(orient="records"),
        "known_gaps": [
            "Free historical yellow-card closing odds are available only for 2025/26.",
            "Historical opening card odds are not available in the free source.",
            "Booking-points markets (where a red is worth two) require a separate target.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
