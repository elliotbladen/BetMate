"""Build the provider-consistent recent UCL training set.

Only matches with SofaScore shotmap xG are admitted to the primary set.  Rows
without xG are quarantined instead of silently replacing xG with goals.
"""
from pathlib import Path
import json
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/ucl"
MATCH = DATA / "matches/ucl_matches_openfootball_repaired.csv"
XG = DATA / "xg/ucl_match_xg_mapped.csv"
OUT = DATA / "matches/ucl_recent_consistent_matches.csv"
QUAR = DATA / "matches/ucl_recent_quarantine.csv"
REPORT = ROOT / "ml/football/reports/ucl_step1_clean_data_audit.json"
REPORT_MD = ROOT / "ml/football/reports/ucl_step1_clean_data_audit.md"

SEASONS = {"2024-25", "2025-26"}

def run():
    m = pd.read_csv(MATCH)
    x = pd.read_csv(XG)
    m = m[m["season"].astype(str).isin(SEASONS)].copy()
    x = x[x["season"].astype(str).isin(SEASONS)].copy()
    # Enforce canonical key and one-to-one provider records.
    x = x.drop_duplicates("match_id", keep="first")
    merged = m.merge(x[["match_id", "home_xg", "away_xg", "xg_source",
                        "sofascore_event_id", "mapping_day_difference",
                        "mapping_score"]], on="match_id", how="left", indicator=True)
    numeric = ["home_goals", "away_goals", "home_xg", "away_xg"]
    for c in numeric:
        merged[c] = pd.to_numeric(merged[c], errors="coerce")
    merged["kickoff_utc_parsed"] = pd.to_datetime(merged["kickoff_utc"], utc=True, errors="coerce")
    valid = (
        merged["_merge"].eq("both") &
        merged["xg_source"].eq("sofascore_shotmap") &
        merged["kickoff_utc_parsed"].notna() &
        merged[["home_club_id", "away_club_id", "home_goals", "away_goals", "home_xg", "away_xg"]].notna().all(axis=1) &
        merged[["home_xg", "away_xg"]].ge(0).all(axis=1) &
        merged[["home_club_id", "away_club_id"]].ne(merged[["away_club_id", "home_club_id"]].values).any(axis=1)
    )
    clean = merged.loc[valid].copy()
    quarantine = merged.loc[~valid].copy()
    clean["Date"] = clean["kickoff_utc_parsed"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    clean["data_contract"] = "ucl_recent_sofascore_xg_v1"
    clean["source_hash"] = hashlib.sha256(XG.read_bytes()).hexdigest()
    keep = ["match_id", "season", "kickoff_utc", "Date", "home_club_id", "away_club_id",
            "home_goals", "away_goals", "home_xg", "away_xg", "xg_source",
            "sofascore_event_id", "mapping_day_difference", "mapping_score",
            "data_contract", "source_hash"]
    clean[keep].sort_values(["Date", "match_id"]).to_csv(OUT, index=False)
    quarantine.to_csv(QUAR, index=False)
    report = {
        "status": "complete",
        "contract": "ucl_recent_sofascore_xg_v1",
        "seasons": sorted(SEASONS),
        "candidate_matches": int(len(m)),
        "clean_matches": int(len(clean)),
        "quarantined_matches": int(len(quarantine)),
        "coverage": float(len(clean) / len(m)) if len(m) else 0.0,
        "by_season_clean": clean["season"].value_counts().sort_index().to_dict(),
        "by_season_quarantine": quarantine["season"].value_counts().sort_index().to_dict(),
        "duplicate_clean_match_ids": int(clean["match_id"].duplicated().sum()),
        "duplicate_provider_event_ids": int(clean["sofascore_event_id"].duplicated().sum()),
        "invalid_dates": int(clean["Date"].isna().sum()),
        "negative_xg": int((clean[["home_xg", "away_xg"]] < 0).any(axis=1).sum()),
        "primary_rule": "No goals fallback in the primary dataset; missing xG is quarantined.",
        "clean_file": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "quarantine_file": str(QUAR.relative_to(ROOT)).replace("\\", "/"),
        "source_hash": hashlib.sha256(XG.read_bytes()).hexdigest(),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# UCL Step 1 — clean provider-consistent data audit", "",
             "Primary training data admits SofaScore shotmap xG only; missing xG is quarantined.", "",
             f"- Candidate recent matches: **{len(m)}**",
             f"- Clean matches: **{len(clean)}** ({report['coverage']:.1%})",
             f"- Quarantined: **{len(quarantine)}**",
             f"- By season (clean): `{report['by_season_clean']}`",
             f"- Duplicate match IDs: **{report['duplicate_clean_match_ids']}**",
             f"- Duplicate provider event IDs: **{report['duplicate_provider_event_ids']}**", "",
             "The 36 missing-xG fixtures remain in quarantine and must not be treated as true xG.", ""]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return report

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
