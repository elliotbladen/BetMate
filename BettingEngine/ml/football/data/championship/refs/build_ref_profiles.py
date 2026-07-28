"""Build the custom Championship referee dataset from raw football-data season files.

Outputs (all in this folder):
  refs_matches.csv    one row per match: goals, yellows, reds, card points
  ref_profiles.csv    one row per referee: goals/cards splits + home-bias metrics
  ref_team_splits.csv one row per (referee, team) with n>=10: favouritism deltas

Also writes refs_workbook.xlsx — everything in one Excel file, tabbed:
  README | Ref Profiles | Ref x Team | Team x Ref | Matches

Card points: yellow = 1, red = 2.
Vault rule: 2025/26 never included.
2023/24 note: Wayback only holds the first 312 matches with reds; the remaining
matches are merged in from the pristine matches CSV with reds = NaN (yellows OK).
"""
import pandas as pd
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw"
PRISTINE = HERE.parent / "matches" / "championship_matches.csv"

SEASONS = {
    "1415": "2014/15", "1516": "2015/16", "1617": "2016/17", "1718": "2017/18",
    "1819": "2018/19", "1920": "2019/20", "2021": "2020/21", "2122": "2021/22",
    "2223": "2022/23", "2324": "2023/24", "2425": "2024/25",
}
COLS = ["Date", "HomeTeam", "AwayTeam", "Referee", "FTHG", "FTAG", "FTR",
        "HY", "AY", "HR", "AR"]


def load_raw():
    frames = []
    for code, label in SEASONS.items():
        df = pd.read_csv(RAW / f"{code}_E1.csv", encoding="latin-1", on_bad_lines="skip")
        raw_dates = df["Date"].astype(str)
        parsed = pd.to_datetime(raw_dates, format="%d/%m/%Y", errors="coerce")
        bad = parsed.isna()
        if bad.any():  # older files use 2-digit years
            parsed[bad] = pd.to_datetime(raw_dates[bad], format="%d/%m/%y", errors="coerce")
        df["Date"] = parsed
        df = df[[c for c in COLS if c in df.columns]].copy()
        df = df[df["FTR"].isin(["H", "D", "A"])]
        df["Season"] = label
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main():
    raw = load_raw()

    # Merge in pristine rows missing from raw (2023/24 back half) — reds NaN
    pri = pd.read_csv(PRISTINE, parse_dates=["Date"])
    pri = pri[pri["Date"] < "2025-08-01"]  # vault
    key = ["Date", "HomeTeam", "AwayTeam"]
    merged_keys = set(map(tuple, raw[key].astype(str).values))
    missing = pri[~pri[key].astype(str).apply(tuple, axis=1).isin(merged_keys)].copy()
    if len(missing):
        missing = missing[["Season", "Date", "HomeTeam", "AwayTeam", "Referee",
                           "FTHG", "FTAG", "FTR", "HY", "AY"]]
        missing["HR"] = np.nan
        missing["AR"] = np.nan
        raw = pd.concat([raw, missing], ignore_index=True)
    raw = raw.sort_values("Date").reset_index(drop=True)

    # Verification vs pristine
    rc_raw = raw.groupby("Season").size()
    rc_pri = pri.groupby("Season").size()
    print("=== VERIFICATION: matches per season (ours vs pristine) ===")
    for s in sorted(set(rc_raw.index) | set(rc_pri.index)):
        a, b = rc_raw.get(s, 0), rc_pri.get(s, 0)
        print(f"  {s}: {a} vs {b} {'OK' if a == b else '<-- MISMATCH'}")
    chk = raw.merge(pri[key + ["FTHG", "FTAG"]], on=key, suffixes=("", "_p"))
    ok = ((chk["FTHG"] == chk["FTHG_p"]) & (chk["FTAG"] == chk["FTAG_p"])).mean()
    print(f"  goals agree with pristine on {ok:.1%} of {len(chk)} joined rows")
    n_nored = raw["HR"].isna().sum()
    print(f"  matches missing red-card data: {n_nored} (2023/24 back half — hotspot fill)")

    # Card points
    raw["home_card_pts"] = raw["HY"].fillna(0) + 2 * raw["HR"].fillna(0)
    raw["away_card_pts"] = raw["AY"].fillna(0) + 2 * raw["AR"].fillna(0)
    raw.to_csv(HERE / "refs_matches.csv", index=False)

    # League baselines
    LG = {
        "home_gpg": raw["FTHG"].mean(), "away_gpg": raw["FTAG"].mean(),
        "home_win": (raw["FTR"] == "H").mean(),
        "home_cpts": raw["home_card_pts"].mean(), "away_cpts": raw["away_card_pts"].mean(),
    }
    print(f"\n=== LEAGUE BASELINES (n={len(raw)}) ===")
    print(f"  home goals/gm {LG['home_gpg']:.3f} | away goals/gm {LG['away_gpg']:.3f} "
          f"| home win {LG['home_win']:.1%}")
    print(f"  home card pts/gm {LG['home_cpts']:.3f} | away card pts/gm {LG['away_cpts']:.3f} "
          f"(away booked {LG['away_cpts']-LG['home_cpts']:+.3f} more)")

    # ── Referee profiles ──
    g = raw.groupby("Referee")
    prof = pd.DataFrame({
        "games": g.size(),
        "first_match": g["Date"].min().dt.date, "last_match": g["Date"].max().dt.date,
        "home_goals_pg": g["FTHG"].mean(), "away_goals_pg": g["FTAG"].mean(),
        "home_win_pct": g["FTR"].apply(lambda x: (x == "H").mean()),
        "draw_pct": g["FTR"].apply(lambda x: (x == "D").mean()),
        "home_card_pts_pg": g["home_card_pts"].mean(),
        "away_card_pts_pg": g["away_card_pts"].mean(),
        "home_yellows_pg": g["HY"].mean(), "away_yellows_pg": g["AY"].mean(),
        "home_reds_pg": g["HR"].mean(), "away_reds_pg": g["AR"].mean(),
    }).reset_index()

    # Bias metrics (all relative to league baseline; positive = home-sided)
    prof["goal_bias"] = (prof["home_goals_pg"] - prof["away_goals_pg"]) - (LG["home_gpg"] - LG["away_gpg"])
    prof["card_bias"] = (prof["away_card_pts_pg"] - prof["home_card_pts_pg"]) - (LG["away_cpts"] - LG["home_cpts"])
    prof["homewin_bias"] = prof["home_win_pct"] - LG["home_win"]
    # z-score for home-win bias so small samples don't dominate rankings
    se = np.sqrt(LG["home_win"] * (1 - LG["home_win"]) / prof["games"])
    prof["homewin_z"] = prof["homewin_bias"] / se
    prof = prof.sort_values("games", ascending=False).round(3)
    prof.to_csv(HERE / "ref_profiles.csv", index=False)

    print(f"\n=== REF PROFILES ({len(prof)} refs) -> ref_profiles.csv ===")
    show = prof[prof["games"] >= 20]
    print(show.to_string(index=False))

    print("\n=== MOST HOME-SIDED REFS (min 50 games, by home-win z-score) ===")
    big = prof[prof["games"] >= 50].sort_values("homewin_z", ascending=False)
    cols = ["Referee", "games", "home_win_pct", "homewin_bias", "homewin_z", "goal_bias", "card_bias"]
    print(big[cols].head(8).to_string(index=False))
    print("\n=== MOST AWAY-SIDED REFS (min 50 games) ===")
    print(big[cols].tail(8).to_string(index=False))

    # ── Ref x team favouritism ──
    home = raw[["Referee", "Season", "HomeTeam", "FTR", "away_card_pts", "home_card_pts"]].rename(
        columns={"HomeTeam": "team"})
    home["pts"] = home["FTR"].map({"H": 3, "D": 1, "A": 0})
    home["card_pts_against_team"] = home["home_card_pts"]
    away = raw[["Referee", "Season", "AwayTeam", "FTR", "away_card_pts", "home_card_pts"]].rename(
        columns={"AwayTeam": "team"})
    away["pts"] = away["FTR"].map({"H": 0, "D": 1, "A": 3})
    away["card_pts_against_team"] = away["away_card_pts"]
    long = pd.concat([home.assign(venue="home"), away.assign(venue="away")], ignore_index=True)

    rows = []
    for (ref, team), grp in long.groupby(["Referee", "team"]):
        if len(grp) < 10:
            continue
        others = long[(long["team"] == team) & (long["Referee"] != ref) &
                      (long["Season"].isin(grp["Season"].unique()))]
        if len(others) < 30:
            continue
        rows.append({
            "Referee": ref, "team": team, "games": len(grp),
            "home_games": (grp["venue"] == "home").sum(),
            "pts_pct_with_ref": grp["pts"].mean() / 3,
            "pts_pct_other_refs": others["pts"].mean() / 3,
            "card_pts_vs_team_with_ref": grp["card_pts_against_team"].mean(),
            "card_pts_vs_team_other_refs": others["card_pts_against_team"].mean(),
        })
    splits = pd.DataFrame(rows)
    splits["pts_delta"] = splits["pts_pct_with_ref"] - splits["pts_pct_other_refs"]
    splits["card_delta"] = splits["card_pts_vs_team_with_ref"] - splits["card_pts_vs_team_other_refs"]
    splits = splits.sort_values("pts_delta", ascending=False).round(3)
    splits.to_csv(HERE / "ref_team_splits.csv", index=False)

    print(f"\n=== REF x TEAM SPLITS ({len(splits)} pairs, n>=10 games) -> ref_team_splits.csv ===")
    print("Teams that OVER-perform with a specific ref (top 12 by points delta):")
    print(splits.head(12).to_string(index=False))
    print("\nTeams that UNDER-perform with a specific ref (bottom 12):")
    print(splits.tail(12).to_string(index=False))
    print("\nBiggest card-treatment gaps (ref books this team much more/less than peers do):")
    bycard = splits.reindex(splits["card_delta"].abs().sort_values(ascending=False).index)
    print(bycard.head(12).to_string(index=False))

    # ── Single Excel workbook, tabbed ──
    readme = pd.DataFrame({
        "column": [
            "CARD POINTS", "goal_bias", "card_bias", "homewin_bias", "homewin_z",
            "pts_pct_with_ref", "pts_pct_other_refs", "pts_delta",
            "card_pts_vs_team_with_ref", "card_delta", "SAMPLE SIZE WARNING",
        ],
        "meaning": [
            "yellow = 1 pt, red = 2 pts",
            "ref's (home - away) goals/gm minus league norm; positive = home teams outscore more than usual",
            "ref's (away - home) card pts/gm minus league norm (+0.35); positive = books away side even more than usual = home-sided whistle",
            "ref's home-win % minus league 43.2%",
            "homewin_bias scaled by sample size — sort by this, not raw %",
            "team's points % (of 3) in matches this ref officiated",
            "same team, same seasons, all other refs",
            "with_ref minus other_refs; positive = team over-performs with this ref",
            "avg card points shown TO this team by this ref",
            "with_ref minus other_refs; positive = ref books this team more than peers do",
            "127 refs tested at once — a few z-scores near ±2 arise by pure chance; treat extremes as suspects, not verdicts",
        ],
    })
    xlsx = HERE / "refs_workbook.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        prof.to_excel(xw, sheet_name="Ref Profiles", index=False, freeze_panes=(1, 1))
        splits.sort_values(["Referee", "pts_delta"], ascending=[True, False]).to_excel(
            xw, sheet_name="Ref x Team", index=False, freeze_panes=(1, 1))
        splits.sort_values(["team", "pts_delta"], ascending=[True, False]).to_excel(
            xw, sheet_name="Team x Ref", index=False, freeze_panes=(1, 1))
        raw.to_excel(xw, sheet_name="Matches", index=False, freeze_panes=(1, 0))
        for ws in xw.book.worksheets:
            ws.auto_filter.ref = ws.dimensions
    print(f"\nWorkbook written: {xlsx}")


if __name__ == "__main__":
    main()
