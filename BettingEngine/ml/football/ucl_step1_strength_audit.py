"""Step 1 audit for UCL inputs and cross-league strength readiness."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/ucl"
REPORT = ROOT / "ml/football/reports/step1_ucl_strength_data_audit.json"

def run():
    matches_path = DATA / "matches/ucl_matches_openfootball_repaired.csv"
    if not matches_path.exists(): matches_path = DATA / "matches/ucl_matches_openfootball.csv"
    m = pd.read_csv(matches_path)
    m["Date"] = pd.to_datetime(m["kickoff_utc"], utc=True, errors="coerce")
    required = ["match_id", "season", "home_club_id", "away_club_id", "home_goals", "away_goals", "Date"]
    missing = [c for c in required if c not in m.columns]
    invalid = int(m["Date"].isna().sum() + m[["home_goals", "away_goals"]].isna().any(axis=1).sum())
    clubs = sorted(set(m.home_club_id.dropna()) | set(m.away_club_id.dropna()))
    duplicate_match_ids = int(m.match_id.duplicated().sum())
    missing_team_ids = int(m[["home_club_id", "away_club_id"]].isna().any(axis=1).sum())
    checksum = hashlib.sha256(matches_path.read_bytes()).hexdigest()
    coeff = DATA / "context/uefa_club_coefficients.csv"
    domestic = list((DATA / "context").glob("*domestic*")) + list((DATA / "strength").glob("*") if (DATA / "strength").exists() else [])
    report = {
        "status": "complete",
        "source": str(matches_path.relative_to(ROOT)).replace("\\", "/"),
        "matches": len(m), "seasons": sorted(m.season.dropna().astype(str).unique().tolist()),
        "clubs": len(clubs), "date_min_utc": m.Date.min().isoformat() if len(m) else None,
        "date_max_utc": m.Date.max().isoformat() if len(m) else None,
        "sha256": checksum, "duplicate_match_ids": duplicate_match_ids, "missing_team_ids": missing_team_ids,
        "missing_required_columns": missing, "invalid_rows": invalid,
        "uefa_coefficient_file_present": coeff.exists(),
        "domestic_strength_files_present": bool(domestic),
        "market_fields_used": False,
        "decision": "fixture identity/date layer ready; coefficient and domestic-strength imports required before activating UEFA prior"
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report

if __name__ == "__main__": print(json.dumps(run(), indent=2))
