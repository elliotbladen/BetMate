#!/usr/bin/env python3
"""Do CONFIRMED STARTING XIs carry O/U 2.5 information the market has not priced?

Second of the "routes back in" listed by TOTALS_SIGNAL_PROBE.md. The first (real xG)
is blocked -- football-data publishes HxG/AxG from 2026/27 only, 60 Championship
matches so far -- so lineups are the only new-information candidate we already hold
data for: ESPN confirmed XIs, 463 matches in 2023/24 and 495 in 2024/25.

Two things make this a different question from the earlier probes, and both cut
against it:

  * The XI is known ~1h before kickoff, so the honest benchmark is the CLOSING line,
    not the opening one. Anything found here is only bettable AFTER lineups drop,
    into the hardest price of the day -- and this account bets at the open.
  * The vault is spent. 2025/26 has starters too (525 matches) but was burned by the
    market-anchored test, so there is no sealed season left to confirm anything on.
    That is why the PRIMARY test below is a powered correlation on all 958 non-vault
    matches, not an under-powered one-season walk-forward.

Primary test: does any XI feature correlate with the market RESIDUAL
(over25 - de-vigged close)? If the market has already priced lineups, that
correlation is zero. n=958 detects |r| >= 0.09 at 80% power, a=0.05.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import log_loss

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ml.football.backtest.efl_totals_signal_probe import fit_predict, load  # noqa: E402
from ml.football.player_layer.backfill_espn_player_stats import ALIASES  # noqa: E402

PLAYER_DIR = ROOT / "ml/football/data/championship/player_layer"
YEARS = [2023, 2024]            # 2025 == vault season 2025/26, deliberately excluded
WINDOW = 10                     # prior matches per team, matching the linear probe

XI_FEATURES = ["xi_shots90_sum", "xi_sot90_sum", "xi_goals90_sum",
               "xi_minshare_sum", "xi_minshare_min"]


def espn_stats() -> pd.DataFrame:
    frames = [pd.read_csv(PLAYER_DIR / f"player_match_stats_espn_{y}.csv", low_memory=False)
              for y in YEARS]
    d = pd.concat(frames, ignore_index=True)
    d["kickoff"] = pd.to_datetime(d.kickoff, format="ISO8601", utc=True)
    d["date"] = d.kickoff.dt.tz_convert(None).dt.normalize()
    d["team_fd"] = d.team.map(lambda x: ALIASES.get(x, x))
    d["home_fd"] = d.home_team.map(lambda x: ALIASES.get(x, x))
    d["away_fd"] = d.away_team.map(lambda x: ALIASES.get(x, x))
    return d.sort_values("kickoff")


def xi_features(stats: pd.DataFrame) -> pd.DataFrame:
    """Per (match, team): what tonight's XI did in that team's PRIOR matches only."""
    rows = []
    for team, g in stats.groupby("team_fd", sort=False):
        matches = list(g.groupby("event_id", sort=False))
        matches.sort(key=lambda kv: kv[1].kickoff.iloc[0])
        for i, (event_id, cur) in enumerate(matches):
            if i < 5:                               # burn-in, same as the linear probe
                continue
            prior = pd.concat([m for _, m in matches[max(0, i - WINDOW):i]])
            xi = cur.loc[cur.starter == 1, "player_id"]
            if len(xi) < 11 or prior.minutes.sum() <= 0:
                continue
            agg = prior.groupby("player_id")[["minutes", "shots", "shots_on_target",
                                              "goals"]].sum()
            mine = agg.reindex(xi.values).fillna(0.0)
            per90 = mine.minutes.clip(lower=1e-9)
            rows.append({
                "event_id": event_id,
                "date": cur.date.iloc[0],
                "home_fd": cur.home_fd.iloc[0], "away_fd": cur.away_fd.iloc[0],
                "team_fd": team, "side": cur.side.iloc[0],
                # a starter with no prior minutes contributes 0 -- that is the point:
                # an XI full of unknowns scores low on capability and low on continuity
                "xi_shots90": float((mine.shots / per90 * 90).sum()),
                "xi_sot90": float((mine.shots_on_target / per90 * 90).sum()),
                "xi_goals90": float((mine.goals / per90 * 90).sum()),
                "xi_minshare": float(mine.minutes.sum() / prior.minutes.sum()),
            })
    return pd.DataFrame(rows)


def assemble() -> pd.DataFrame:
    xi = xi_features(espn_stats())
    wide = xi.pivot_table(index=["date", "home_fd", "away_fd"], columns="side",
                          values=["xi_shots90", "xi_sot90", "xi_goals90", "xi_minshare"])
    wide.columns = [f"{side}_{col}" for col, side in wide.columns]
    wide = wide.dropna().reset_index()
    for c in ("shots90", "sot90", "goals90", "minshare"):
        wide[f"xi_{c}_sum"] = wide[f"home_xi_{c}"] + wide[f"away_xi_{c}"]
    wide["xi_minshare_min"] = wide[["home_xi_minshare", "away_xi_minshare"]].min(axis=1)

    fd = load()                                   # vault already dropped inside load()
    fd["date"] = fd.Date.dt.normalize()
    m = fd.merge(wide, left_on=["date", "HomeTeam", "AwayTeam"],
                 right_on=["date", "home_fd", "away_fd"], how="inner")
    return m


def main() -> None:
    m = assemble()
    print(f"ESPN XIs joined to football-data matches: {len(m)}"
          f"   seasons {sorted(m.Season.unique())}")
    m = m[m.mkt_close.notna() & m.mkt_open.notna()].copy()
    print(f"  ... with opening AND closing totals odds: {len(m)}")
    if len(m) < 200:
        print("too few joined rows to test"); return

    m["resid"] = m.over25 - m.mkt_close
    print(f"\n=== PRIMARY: does the XI correlate with what the close got wrong? ===")
    print(f"{'feature':<20}{'r vs over25':>13}{'p':>9}{'r vs residual':>16}{'p':>9}")
    for f in XI_FEATURES:
        r1, p1 = pearsonr(m[f], m.over25)
        r2, p2 = pearsonr(m[f], m.resid)
        print(f"{f:<20}{r1:>+13.4f}{p1:>9.4f}{r2:>+16.4f}{p2:>9.4f}")
    r_mkt, p_mkt = pearsonr(m.mkt_close, m.over25)
    print(f"{'(the close itself)':<20}{r_mkt:>+13.4f}{p_mkt:>9.4f}"
          f"{'--':>16}{'--':>9}")
    print(f"\n  n={len(m)} detects |r| >= {2.8 / np.sqrt(len(m)):.3f} at 80% power, a=0.05")

    seasons = sorted(m.Season.unique())
    if len(seasons) >= 2:
        te = m[m.Season == seasons[-1]]
        tr = m[m.Season != seasons[-1]]
        print(f"\n=== SECONDARY: walk-forward, train {seasons[:-1]} -> test {seasons[-1]} ===")
        print(f"  train {len(tr)}  test {len(te)}   (ONE test season: under-powered by "
              f"design, read as a sanity check, not evidence)")
        y = te.over25.values
        p_mkt_only, _ = fit_predict(tr, te, [], "mkt_close")
        p_both, _ = fit_predict(tr, te, XI_FEATURES, "mkt_close")
        ll_c, ll_m, ll_b = (log_loss(y, te.mkt_close.values),
                            log_loss(y, p_mkt_only), log_loss(y, p_both))
        print(f"  closing line     {ll_c:.5f}")
        print(f"  market-only      {ll_m:.5f}")
        print(f"  market + XI      {ll_b:.5f}   gain {ll_m - ll_b:+.5f}"
              f"{'' if ll_b < ll_m else '   (worse)'}")

    out = ROOT / "outputs/football/championship/_research"
    out.mkdir(parents=True, exist_ok=True)
    m[["Date", "Season", "HomeTeam", "AwayTeam", "total", "over25", "mkt_open",
       "mkt_close", "resid"] + XI_FEATURES].to_csv(out / "totals_lineup_probe.csv",
                                                   index=False)
    print(f"\nwrote {out/'totals_lineup_probe.csv'}")


if __name__ == "__main__":
    main()
