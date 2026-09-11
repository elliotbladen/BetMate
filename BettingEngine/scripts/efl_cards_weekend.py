#!/usr/bin/env python3
"""Weekly Championship cards over/under bet finder.

Run it on a Friday once the EFL has published appointments:

    python scripts/efl_cards_weekend.py --start 2026-09-11 --end 2026-09-13 --round 7

What it does, in order:
  1. pulls the round's fixtures AND referees from the FotMob match API — efl.com is a
     JS shell that will not render server-side, Transfermarkt shows "Referee: Unknown"
     until kickoff, and ESPN only fills the official in once the match starts;
  2. shrinks each referee's and each club's card rate toward the league mean by its own
     sample noise (empirical Bayes);
  3. combines them into an expected match card count and converts with Poisson;
  4. writes a ranked markdown table plus a bets CSV for anything clearing the edge bar.

Why this is worth betting when the goals version of the same matrix is not: referee card
tendency PERSISTS season to season (r=+0.42, p=0.0001 over 80 referee-season pairs),
where referee O/U 2.5 goals edge does not (r=+0.08). The edge here is the referee, not
the fixture — so a thin referee sample means no bet, however inviting the clubs look.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson

ROOT = Path(__file__).resolve().parents[1]
MATCHES = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
FOTMOB = "https://www.fotmob.com/api/data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SEASONS = ("2022/23", "2023/24", "2024/25", "2025/26", "2026/27")

# FotMob display name -> football-data.co.uk name. Unmapped clubs abort the run rather
# than silently scoring a fixture off league-average priors.
TEAMS = {
    "West Ham United": "West Ham", "Wrexham": "Wrexham", "Bolton Wanderers": "Bolton",
    "Cardiff City": "Cardiff", "Derby County": "Derby", "Birmingham City": "Birmingham",
    "West Bromwich Albion": "West Brom", "Queens Park Rangers": "QPR",
    "Blackburn Rovers": "Blackburn", "Millwall": "Millwall",
    "Charlton Athletic": "Charlton", "Portsmouth": "Portsmouth",
    "Middlesbrough": "Middlesbrough", "Norwich City": "Norwich",
    "Preston North End": "Preston", "Lincoln City": "Lincoln",
    "Southampton": "Southampton", "Bristol City": "Bristol City",
    "Swansea City": "Swansea", "Burnley": "Burnley", "Watford": "Watford",
    "Stoke City": "Stoke", "Sheffield United": "Sheffield United",
    "Wolverhampton Wanderers": "Wolves", "Hull City": "Hull", "Coventry City": "Coventry",
    "Leicester City": "Leicester", "Ipswich Town": "Ipswich", "Luton Town": "Luton",
    "Plymouth Argyle": "Plymouth", "Oxford United": "Oxford", "Sheffield Wednesday": "Sheff Wed",
}


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_round(start: date, end: date, pause: float) -> list[dict]:
    """Championship fixtures + appointed referees between two dates."""
    out = []
    day = start
    while day <= end:
        board = get(f"{FOTMOB}/matches?date={day:%Y%m%d}")
        for league in board.get("leagues", []):
            if league.get("ccode") != "ENG" or "Championship" not in league.get("name", ""):
                continue
            for match in league.get("matches", []):
                time.sleep(pause)
                detail = get(f"{FOTMOB}/matchDetails?matchId={match['id']}")
                info = detail.get("content", {}).get("matchFacts", {}).get("infoBox", {})
                referee = (info.get("Referee") or {}).get("text")
                out.append({"date": day.isoformat(), "match_id": match["id"],
                            "home_raw": match["home"]["name"],
                            "away_raw": match["away"]["name"], "referee_full": referee})
        day += timedelta(days=1)
    return out


def fd_referee(full: str | None) -> str | None:
    """'Matt Donohue' -> 'M Donohue' (football-data.co.uk convention)."""
    if not full:
        return None
    parts = full.split()
    return f"{parts[0][0]} {' '.join(parts[1:])}" if len(parts) > 1 else full


def shrink(frame: pd.DataFrame, league_mean: float) -> pd.DataFrame:
    """Empirical Bayes: keep the share of a deviation that is not explicable as noise."""
    within = (frame["var"] / frame["size"])
    tau2 = max(frame["mean"].var(ddof=1) - within.mean(), 0.0)
    frame = frame.copy()
    frame["keep"] = tau2 / (tau2 + within)
    frame["shrunk"] = league_mean + (frame["mean"] - league_mean) * frame["keep"]
    frame.attrs["tau"] = float(np.sqrt(tau2))
    return frame


def history() -> tuple[pd.DataFrame, pd.DataFrame, float]:
    d = pd.read_csv(MATCHES, low_memory=False)
    d["cards"] = pd.to_numeric(d.HY, errors="coerce") + pd.to_numeric(d.AY, errors="coerce")
    d["Referee"] = d.Referee.astype(str).str.strip()
    a = d[d.Season.isin(SEASONS) & d.cards.notna()].copy()
    league = float(a.cards.mean())

    refs = a.groupby("Referee").cards.agg(["size", "mean", "var"])
    refs = shrink(refs[refs["size"] >= 10], league)
    refs["o35"] = a.groupby("Referee").cards.apply(lambda x: (x > 3.5).mean() * 100)

    long = pd.concat([a.rename(columns={"HomeTeam": "team"})[["team", "cards"]],
                      a.rename(columns={"AwayTeam": "team"})[["team", "cards"]]])
    teams = shrink(long.groupby("team").cards.agg(["size", "mean", "var"]), league)
    return refs, teams, league


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--season", default="2026-27")
    ap.add_argument("--line", type=float, default=3.5)
    ap.add_argument("--min-prob", type=float, default=0.57,
                    help="only bet a side priced above this (default 0.57)")
    ap.add_argument("--min-ref-games", type=int, default=25,
                    help="referees below this are unpriceable — no bet (default 25)")
    ap.add_argument("--pause", type=float, default=1.2)
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()
    fixtures = fetch_round(start, end, args.pause)
    if not fixtures:
        sys.exit("No Championship fixtures found in that window.")
    unmapped = {f[k] for f in fixtures for k in ("home_raw", "away_raw")} - set(TEAMS)
    if unmapped:
        sys.exit(f"Unmapped club name(s): {sorted(unmapped)} — add to TEAMS and re-run.")

    refs, teams, league = history()
    print(f"{len(fixtures)} fixtures {args.start}..{args.end}  |  league {league:.2f} cards/game"
          f"  |  tau ref {refs.attrs['tau']:.3f} / club {teams.attrs['tau']:.3f}")
    missing = [f for f in fixtures if not f["referee_full"]]
    if missing:
        print(f"  ! {len(missing)} fixture(s) with no referee published yet: "
              f"{', '.join(f['home_raw'] + ' v ' + f['away_raw'] for f in missing)}")

    rows = []
    for f in fixtures:
        home, away = TEAMS[f["home_raw"]], TEAMS[f["away_raw"]]
        ref = fd_referee(f["referee_full"])
        known = ref in refs.index
        ref_n = int(refs.loc[ref, "size"]) if known else 0
        ref_cards = float(refs.loc[ref, "shrunk"]) if known else league
        team_cards = float(np.mean([teams.loc[t, "shrunk"] if t in teams.index else league
                                    for t in (home, away)]))
        lam = ref_cards * team_cards / league
        p_over = float(1 - poisson.cdf(np.floor(args.line), lam))
        rows.append({
            "date": f["date"], "home": home, "away": away,
            "referee": ref or "UNPUBLISHED", "ref_games": ref_n,
            "ref_cards_pg": round(ref_cards, 2),
            "ref_o35_pct": round(float(refs.loc[ref, "o35"]), 1) if known else None,
            "team_cards_pg": round(team_cards, 2), "lambda": round(lam, 2),
            "p_over": round(p_over * 100, 1), "p_under": round((1 - p_over) * 100, 1),
            "be_over": round(1 / p_over, 2) if p_over else None,
            "be_under": round(1 / (1 - p_over), 2) if p_over < 1 else None,
            "priceable": known and ref_n >= args.min_ref_games,
        })
    table = pd.DataFrame(rows).sort_values("p_over", ascending=False)

    bets = []
    for _, x in table.iterrows():
        if not x.priceable:
            continue
        for side, prob in (("Over", x.p_over / 100), ("Under", x.p_under / 100)):
            if prob >= args.min_prob:
                bets.append({
                    "round": args.round, "match_date": x.date, "home": x.home, "away": x.away,
                    "market": f"Cards O/U {args.line}", "selection": f"{side} {args.line} cards",
                    "referee": x.referee, "referee_games": x.ref_games,
                    "referee_cards_pg": x.ref_cards_pg, "referee_o35_pct": x.ref_o35_pct,
                    "model_probability": round(prob, 4),
                    "min_price": round(1 / prob, 2),
                    "odds_taken": "", "stake_units": 1.0, "bookmaker": "",
                    "result": "", "pnl": "",
                    "status": "pending_placement",
                    "note": f"lambda {x['lambda']} cards. Edge is the referee, not the fixture. "
                            f"Do not take below {round(1 / prob, 2)}.",
                })

    out = ROOT / f"outputs/football/championship/{args.season}/gw{args.round:02d}/_supporting"
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "cards_all_fixtures.csv", index=False)
    bets_path = out / "cards_bets.csv"
    if bets:
        pd.DataFrame(bets).to_csv(bets_path, index=False)
    print(f"\n{'fixture':<30}{'referee':<13}{'n':>4}{'refC/g':>8}{'λ':>7}"
          f"{'P(over)':>9}{'BEo':>7}{'BEu':>7}  bet")
    for _, x in table.iterrows():
        pick = ""
        if x.priceable:
            if x.p_over / 100 >= args.min_prob:
                pick = f"OVER  @{x.be_over}+"
            elif x.p_under / 100 >= args.min_prob:
                pick = f"UNDER @{x.be_under}+"
        elif x.referee == "UNPUBLISHED":
            pick = "no referee yet"
        else:
            pick = f"referee too thin ({x.ref_games})"
        print(f"{x.home + ' v ' + x.away:<30}{x.referee:<13}{x.ref_games:>4}"
              f"{x.ref_cards_pg:>8.2f}{x['lambda']:>7.2f}{x.p_over:>8.1f}%"
              f"{x.be_over or 0:>7.2f}{x.be_under or 0:>7.2f}  {pick}")
    print(f"\nwrote {out/'cards_all_fixtures.csv'}")
    print(f"      {bets_path}" if bets else "      no selection cleared the bar")


if __name__ == "__main__":
    main()
