"""
Full situational matrix for an NRL matchup.
Checks: day/night, rest days, day of week, moon phase, home streaks,
        recent form, blowout bounce, finals context.

Usage: uv run --with openpyxl --with pandas python scripts/h2h_matrix.py Storm Raiders
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

XLSX = Path("C:/Users/ElliotBladen/Apps/data/nrl/historical/latest.xlsx")
MIN_N = 5  # minimum sample to report an edge


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load() -> pd.DataFrame:
    df = pd.read_excel(XLSX, header=1)
    df = df[df["Date"].notna()].copy()
    df = df[df["Home Team"].astype(str).str.strip() != "Home Team"].copy()
    df["date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["kickoff_time"] = df["Kick-off (local)"]
    df["home_score"] = pd.to_numeric(df["Home Score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["Away Score"], errors="coerce")
    df["home_line"] = pd.to_numeric(df.get("Home Line Close"), errors="coerce")
    df["away_line"] = pd.to_numeric(df.get("Away Line Close"), errors="coerce")
    df["home_h2h"] = pd.to_numeric(df.get("Home Odds Close"), errors="coerce")
    df["away_h2h"] = pd.to_numeric(df.get("Away Odds Close"), errors="coerce")
    df["margin"] = df["home_score"] - df["away_score"]
    df["total"] = df["home_score"] + df["away_score"]
    df["is_finals"] = df.get("Play Off Game?", pd.Series()).astype(str).str.strip().str.upper() == "Y"
    return df.sort_values("date").reset_index(drop=True)


def match_team(s: pd.Series, name: str) -> pd.Series:
    return s.astype(str).str.lower().str.contains(name.lower(), na=False)


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

LUNAR_CYCLE = 29.530588853
KNOWN_NEW_MOON = datetime(2000, 1, 6)  # verified new moon date

def moon_age(dt) -> float:
    """Days since last new moon (0 = new, ~14.8 = full)."""
    if pd.isna(dt):
        return float("nan")
    d = pd.Timestamp(dt)
    days = (d - pd.Timestamp(KNOWN_NEW_MOON)).days
    return days % LUNAR_CYCLE


def is_full_moon(dt, window: int = 3) -> bool:
    age = moon_age(dt)
    return not math.isnan(age) and abs(age - 14.77) <= window


def kickoff_hour(row) -> int | None:
    """Extract hour from Kick-off (local) column."""
    t = row.get("kickoff_time")
    if pd.isna(t):
        return None
    if hasattr(t, "hour"):
        return t.hour
    try:
        return int(str(t).split(":")[0])
    except Exception:
        return None


def is_night_game(row, cutoff_hour: int = 17) -> bool | None:
    h = kickoff_hour(row)
    if h is None:
        return None
    return h >= cutoff_hour


def day_of_week(dt) -> str:
    if pd.isna(dt):
        return "?"
    return pd.Timestamp(dt).strftime("%A")


def rest_days_before(df: pd.DataFrame, team: str, game_date) -> int | None:
    """Days since this team last played, looking at all games."""
    team_games = df[
        match_team(df["Home Team"], team) | match_team(df["Away Team"], team)
    ]["date"].dropna().sort_values()
    game_date = pd.Timestamp(game_date)
    prior = team_games[team_games < game_date]
    if prior.empty:
        return None
    last = prior.iloc[-1]
    return (game_date - last).days


def home_win_streak(df: pd.DataFrame, team: str, before_date) -> int:
    """How many consecutive home wins has team had going into this game."""
    home_games = df[
        match_team(df["Home Team"], team) & df["date"].notna()
    ].sort_values("date")
    before_date = pd.Timestamp(before_date)
    prior = home_games[home_games["date"] < before_date]
    streak = 0
    for _, row in prior.iloc[::-1].iterrows():
        if row["margin"] > 0:
            streak += 1
        else:
            break
    return streak


def away_loss_streak(df: pd.DataFrame, team: str, before_date) -> int:
    """Consecutive away losses going into this game."""
    away_games = df[
        match_team(df["Away Team"], team) & df["date"].notna()
    ].sort_values("date")
    before_date = pd.Timestamp(before_date)
    prior = away_games[away_games["date"] < before_date]
    streak = 0
    for _, row in prior.iloc[::-1].iterrows():
        if row["margin"] < 0:  # home team won = away team lost
            streak += 1
        else:
            break
    return streak


def last_margin(df: pd.DataFrame, team: str, before_date) -> int | None:
    """Margin from team's perspective in their last game."""
    team_games = df[
        (match_team(df["Home Team"], team) | match_team(df["Away Team"], team)) &
        df["date"].notna()
    ].sort_values("date")
    before_date = pd.Timestamp(before_date)
    prior = team_games[team_games["date"] < before_date]
    if prior.empty:
        return None
    row = prior.iloc[-1]
    if str(row["Home Team"]).lower().find(team.lower()) >= 0:
        return int(row["margin"]) if pd.notna(row["margin"]) else None
    else:
        return int(-row["margin"]) if pd.notna(row["margin"]) else None


# ---------------------------------------------------------------------------
# Edge reporter
# ---------------------------------------------------------------------------

def edge_report(label: str, games: pd.DataFrame, home_team: str, n_total: int) -> None:
    n = len(games)
    if n < MIN_N:
        return
    wins = int((games["margin"] > 0).sum())
    win_pct = wins / n * 100
    cov_games = games[games["home_line"].notna() & (games["home_line"] < 0)].copy()
    if len(cov_games) >= 3:
        cov_games["covered"] = (cov_games["margin"] + cov_games["home_line"]) > 0
        cov_pct = cov_games["covered"].mean() * 100
        cov_str = f"  hcap cover {cov_pct:.0f}% (n={len(cov_games)})"
    else:
        cov_str = ""
    avg_mg = games["margin"].mean()
    pct_of_total = n / n_total * 100
    print(f"  {label:<45} {wins}/{n} wins ({win_pct:.0f}%) | avg margin {avg_mg:+.1f}{cov_str}")


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def enrich_h2h(df: pd.DataFrame, h2h: pd.DataFrame, team_a: str, team_b: str) -> pd.DataFrame:
    """Add situational columns to H2H games."""
    records = []
    for _, row in h2h.iterrows():
        dt = row["date"]
        rec = dict(row)
        rec["dow"] = day_of_week(dt)
        rec["night_game"] = is_night_game(row)
        rec["full_moon"] = is_full_moon(dt)
        rec["moon_age"] = round(moon_age(dt), 1)

        # Storm rest (team_a)
        storm_is_home = str(row["Home Team"]).lower().find(team_a.lower()) >= 0
        rec["storm_rest"] = rest_days_before(df, team_a, dt)
        rec["raiders_rest"] = rest_days_before(df, team_b, dt)
        if rec["storm_rest"] and rec["raiders_rest"]:
            rec["rest_diff"] = rec["storm_rest"] - rec["raiders_rest"]  # positive = Storm more rest
        else:
            rec["rest_diff"] = None

        # Streaks
        if storm_is_home:
            rec["home_win_streak"] = home_win_streak(df, team_a, dt)
        else:
            rec["home_win_streak"] = home_win_streak(df, team_b, dt)

        rec["raiders_away_loss_streak"] = away_loss_streak(df, team_b, dt)

        # Last game margin (from each team's perspective)
        rec["storm_last_margin"] = last_margin(df, team_a, dt)
        rec["raiders_last_margin"] = last_margin(df, team_b, dt)

        # Reframe margin as "Storm margin" (positive = Storm win regardless of home/away)
        if storm_is_home:
            rec["storm_margin"] = row["margin"]
        else:
            rec["storm_margin"] = -row["margin"]

        rec["storm_is_home"] = storm_is_home
        records.append(rec)

    return pd.DataFrame(records)


def analyse(df: pd.DataFrame, team_a: str, team_b: str) -> None:
    h2h_raw = df[
        (match_team(df["Home Team"], team_a) & match_team(df["Away Team"], team_b)) |
        (match_team(df["Home Team"], team_b) & match_team(df["Away Team"], team_a))
    ].copy().sort_values("date", ascending=False)

    n_total = len(h2h_raw)
    print(f"\n{'='*70}")
    print(f"  {team_a.upper()} vs {team_b.upper()} -- FULL SITUATIONAL MATRIX")
    print(f"{'='*70}")
    print(f"  Dataset: {n_total} H2H games  |  min sample to report: {MIN_N}")

    print("\n  Enriching with situational features (rest days etc. takes ~15s)...")
    h2h = enrich_h2h(df, h2h_raw, team_a, team_b)

    # Storm at home subset (relevant for this week's game)
    at_home = h2h[h2h["storm_is_home"]]
    n_home = len(at_home)
    print(f"  {team_a} at home vs {team_b}: {n_home} games")

    # ---------- DAY OF WEEK ----------
    print(f"\n{'='*70}")
    print("  DAY OF WEEK (Storm at home, home team perspective)")
    print(f"{'='*70}")
    for dow in ["Thursday", "Friday", "Saturday", "Sunday", "Monday"]:
        sub = at_home[at_home["dow"] == dow]
        edge_report(f"  {dow}", sub, team_a, n_home)

    # ---------- DAY vs NIGHT ----------
    print(f"\n{'='*70}")
    print("  DAY vs NIGHT GAME (Storm at home)")
    print(f"{'='*70}")
    day_games = at_home[at_home["night_game"] == False]
    night_games = at_home[at_home["night_game"] == True]
    edge_report("  Day game (kickoff <17:00)", day_games, team_a, n_home)
    edge_report("  Night game (kickoff >=17:00)", night_games, team_a, n_home)

    # ---------- REST DAYS ----------
    print(f"\n{'='*70}")
    print("  REST DAYS")
    print(f"{'='*70}")

    rest_data = h2h[h2h["storm_rest"].notna() & h2h["raiders_rest"].notna()].copy()
    n_rest = len(rest_data)

    if n_rest > 0:
        short = rest_data[rest_data["storm_rest"] <= 6]
        normal = rest_data[(rest_data["storm_rest"] >= 7) & (rest_data["storm_rest"] <= 8)]
        long_r = rest_data[rest_data["storm_rest"] >= 9]
        print(f"  -- Storm rest days --  (home+away combined, n={n_rest})")
        edge_report("  Storm short rest (<=6 days)", short, team_a, n_rest)
        edge_report("  Storm normal rest (7-8 days)", normal, team_a, n_rest)
        edge_report("  Storm long rest (9+ days / bye)", long_r, team_a, n_rest)

        print()
        short_r = rest_data[rest_data["raiders_rest"] <= 6]
        normal_r = rest_data[(rest_data["raiders_rest"] >= 7) & (rest_data["raiders_rest"] <= 8)]
        long_rr = rest_data[rest_data["raiders_rest"] >= 9]
        print(f"  -- Raiders rest days --  (n={n_rest})")
        edge_report("  Raiders short rest (<=6 days)", short_r, team_a, n_rest)
        edge_report("  Raiders normal rest (7-8 days)", normal_r, team_a, n_rest)
        edge_report("  Raiders long rest (9+ days / bye)", long_rr, team_a, n_rest)

        print()
        rest_diff_data = h2h[h2h["rest_diff"].notna()].copy()
        storm_more = rest_diff_data[rest_diff_data["rest_diff"] > 0]
        storm_less = rest_diff_data[rest_diff_data["rest_diff"] < 0]
        equal_rest = rest_diff_data[rest_diff_data["rest_diff"] == 0]
        print(f"  -- Rest days differential (n={len(rest_diff_data)}) --")
        edge_report("  Storm has MORE rest than Raiders", storm_more, team_a, len(rest_diff_data))
        edge_report("  Storm has LESS rest than Raiders", storm_less, team_a, len(rest_diff_data))
        edge_report("  Equal rest", equal_rest, team_a, len(rest_diff_data))

    # ---------- MOON PHASE ----------
    print(f"\n{'='*70}")
    print("  MOON PHASE")
    print(f"{'='*70}")
    full_moon_games = h2h[h2h["full_moon"] == True]
    not_full = h2h[h2h["full_moon"] == False]
    edge_report("  Full moon (within 3 days)", full_moon_games, team_a, n_total)
    edge_report("  Not full moon", not_full, team_a, n_total)

    # ---------- STORM HOME STREAK ----------
    print(f"\n{'='*70}")
    print("  STORM HOME WIN STREAK ENTERING GAME (Storm at home only)")
    print(f"{'='*70}")
    at_home_s = at_home[at_home["home_win_streak"].notna()].copy()
    no_str = at_home_s[at_home_s["home_win_streak"] == 0]
    mid_str = at_home_s[(at_home_s["home_win_streak"] >= 1) & (at_home_s["home_win_streak"] <= 3)]
    long_str = at_home_s[at_home_s["home_win_streak"] >= 4]
    edge_report("  Entering on 0 home win streak", no_str, team_a, n_home)
    edge_report("  Entering on 1-3 home win streak", mid_str, team_a, n_home)
    edge_report("  Entering on 4+ home win streak", long_str, team_a, n_home)

    # ---------- RAIDERS AWAY LOSS STREAK ----------
    print(f"\n{'='*70}")
    print("  RAIDERS AWAY LOSS STREAK ENTERING GAME")
    print(f"{'='*70}")
    ral_data = h2h[h2h["raiders_away_loss_streak"].notna()].copy()
    no_loss = ral_data[ral_data["raiders_away_loss_streak"] == 0]
    mid_loss = ral_data[(ral_data["raiders_away_loss_streak"] >= 1) & (ral_data["raiders_away_loss_streak"] <= 2)]
    long_loss = ral_data[ral_data["raiders_away_loss_streak"] >= 3]
    edge_report("  Raiders on 0 away loss streak", no_loss, team_a, n_total)
    edge_report("  Raiders on 1-2 away loss streak", mid_loss, team_a, n_total)
    edge_report("  Raiders on 3+ away loss streak", long_loss, team_a, n_total)

    # ---------- LAST GAME FORM ----------
    print(f"\n{'='*70}")
    print("  LAST GAME FORM")
    print(f"{'='*70}")
    form_data = h2h[h2h["storm_last_margin"].notna()].copy()
    storm_won_last = form_data[form_data["storm_last_margin"] > 0]
    storm_lost_last = form_data[form_data["storm_last_margin"] < 0]
    storm_blowout_last = form_data[form_data["storm_last_margin"] >= 20]
    edge_report("  Storm won their last game", storm_won_last, team_a, len(form_data))
    edge_report("  Storm lost their last game", storm_lost_last, team_a, len(form_data))
    edge_report("  Storm blowout win last game (20+)", storm_blowout_last, team_a, len(form_data))

    form_r = h2h[h2h["raiders_last_margin"].notna()].copy()
    raiders_won_last = form_r[form_r["raiders_last_margin"] > 0]
    raiders_lost_last = form_r[form_r["raiders_last_margin"] < 0]
    raiders_blowout_loss = form_r[form_r["raiders_last_margin"] <= -20]
    edge_report("  Raiders won their last game", raiders_won_last, team_a, len(form_r))
    edge_report("  Raiders lost their last game", raiders_lost_last, team_a, len(form_r))
    edge_report("  Raiders big loss last game (20+)", raiders_blowout_loss, team_a, len(form_r))

    # ---------- FINALS vs REGULAR SEASON ----------
    print(f"\n{'='*70}")
    print("  CONTEXT")
    print(f"{'='*70}")
    finals = h2h[h2h["is_finals"] == True]
    regular = h2h[h2h["is_finals"] == False]
    edge_report("  Finals games", finals, team_a, n_total)
    edge_report("  Regular season", regular, team_a, n_total)

    # ---------- HANDICAP COVER SUMMARY (Storm at home as fav) ----------
    print(f"\n{'='*70}")
    print("  HANDICAP COVER BREAKDOWN (Storm at home as favourite)")
    print(f"{'='*70}")
    fav = at_home[at_home["home_line"].notna() & (at_home["home_line"] < 0)].copy()
    fav["covered"] = (fav["margin"] + fav["home_line"]) > 0
    n_fav = len(fav)
    if n_fav > 0:
        print(f"  Overall: {int(fav['covered'].sum())}/{n_fav} covered ({fav['covered'].mean()*100:.0f}%)")
        print(f"  Avg line: {fav['home_line'].mean():.1f}  |  Avg actual margin: {fav['margin'].mean():+.1f}")

        # Cover by line band
        light = fav[fav["home_line"] >= -8]
        heavy = fav[fav["home_line"] < -8]
        if len(light) >= 3:
            print(f"  Line 0 to -8:   {int(light['covered'].sum())}/{len(light)} covered ({light['covered'].mean()*100:.0f}%)")
        if len(heavy) >= 3:
            print(f"  Line >-8:       {int(heavy['covered'].sum())}/{len(heavy)} covered ({heavy['covered'].mean()*100:.0f}%)")

        # Cover by day/night
        for night_val, lbl in [(True, "Night"), (False, "Day")]:
            sub = fav[fav["night_game"] == night_val]
            if len(sub) >= 3:
                print(f"  {lbl} game cover:  {int(sub['covered'].sum())}/{len(sub)} ({sub['covered'].mean()*100:.0f}%)")

        # Cover with long vs short rest
        sub_rest = fav[fav["storm_rest"].notna()]
        short_c = sub_rest[sub_rest["storm_rest"] <= 6]
        long_c = sub_rest[sub_rest["storm_rest"] >= 9]
        if len(short_c) >= 3:
            print(f"  Short rest cover: {int(short_c['covered'].sum())}/{len(short_c)} ({short_c['covered'].mean()*100:.0f}%)")
        if len(long_c) >= 3:
            print(f"  Long rest cover:  {int(long_c['covered'].sum())}/{len(long_c)} ({long_c['covered'].mean()*100:.0f}%)")

    # ---------- LAST 12 H2H RAW ----------
    print(f"\n{'='*70}")
    print("  LAST 12 H2H WITH SITUATIONAL DATA")
    print(f"{'='*70}")
    print(f"  {'Date':<12} {'Home':<16} {'Sc':<9} {'Away':<16} {'Line':>7} {'Cvr':>5} {'DOW':<4} {'Ng':>3} {'FM':>3} {'SRst':>5} {'RRst':>5}")
    print("  " + "-" * 90)
    for _, row in h2h.head(12).iterrows():
        dt = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "?"
        ht = str(row["Home Team"])[:14]
        at = str(row["Away Team"])[:14]
        sc = f"{int(row['home_score']) if pd.notna(row.get('home_score')) else '?'}-{int(row['away_score']) if pd.notna(row.get('away_score')) else '?'}"
        hl = f"{row['home_line']:+.1f}" if pd.notna(row.get("home_line")) else "?"
        if pd.notna(row.get("home_line")) and pd.notna(row.get("margin")):
            cvr = "Y" if (row["margin"] + row["home_line"]) > 0 else "N"
        else:
            cvr = "?"
        dow = row.get("dow", "?")[:3]
        ng = "Y" if row.get("night_game") else "N"
        fm = "Y" if row.get("full_moon") else "N"
        sr = f"{int(row['storm_rest'])}" if pd.notna(row.get("storm_rest")) else "?"
        rr = f"{int(row['raiders_rest'])}" if pd.notna(row.get("raiders_rest")) else "?"
        print(f"  {dt:<12} {ht:<16} {sc:<9} {at:<16} {hl:>7} {cvr:>5} {dow:<4} {ng:>3} {fm:>3} {sr:>5} {rr:>5}")

    print()


def main():
    team_a = sys.argv[1] if len(sys.argv) > 1 else "Storm"
    team_b = sys.argv[2] if len(sys.argv) > 2 else "Raiders"
    print(f"Loading {XLSX.name}...")
    df = load()
    print(f"Loaded {len(df)} games")
    analyse(df, team_a, team_b)


if __name__ == "__main__":
    main()
