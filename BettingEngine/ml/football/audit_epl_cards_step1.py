"""Audit the EPL card-model data foundation before feature work begins."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
MATCHES = ROOT / "data" / "epl" / "matches" / "epl_matches.csv"
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
        "season_coverage": season.reset_index().to_dict(orient="records"),
        "known_gaps": [
            "The match file contains yellow cards but no HR/AR red-card columns.",
            "The match file contains no historical Over/Under 3.5 cards prices.",
            "Bookmaker red-card settlement treatment must be confirmed before live pricing.",
            "Historical opening and closing card prices need a separate source and match join.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
