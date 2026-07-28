"""Referee tier experiment (Championship): can richer, shrunk ref features improve
the model out-of-sample and produce positive CLV vs Pinnacle opening?

Features (all expanding-window, prior matches only — leak-free):
  f_hg      ref home-goals/gm deviation from expanding league mean, shrunk n/(n+k)
  f_ag      ref away-goals/gm deviation, shrunk
  f_hw      ref home-win-rate deviation, shrunk
  f_card    ref (away-home) card-pts gap deviation from league norm, shrunk
  f_team_h  home team's pts/3 with this ref minus with other refs (prior), shrunk
  f_team_a  same for away team

Walk-forward: test 2022/23 (fit on 21/22), 2023/24 (fit 21/22+22/23),
2024/25 (fit all three). Adjusts base model logits via multinomial LR.

Run:  python ml/football/backtest/ref_experiment.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).parent.parent
CLV_CSV = ROOT / "data" / "championship" / "clv" / "backtest_results.csv"
REFS_CSV = ROOT / "data" / "championship" / "refs" / "refs_matches.csv"
MATCHES_CSV = ROOT / "data" / "championship" / "matches" / "championship_matches.csv"

K_GRID = [20, 50, 100]          # shrinkage strengths to try (chosen on train folds)
TEST_ORDER = ["2021/22", "2022/23", "2023/24", "2024/25"]
EDGE_THRESHOLDS = [0.05, 0.08]
DECISION_SHIFT = 0.015          # "ref changed the price" segment: |dP| >= 1.5pp


def build_ref_features(refs: pd.DataFrame, k: float) -> pd.DataFrame:
    """One row per match with expanding, shrunk ref features known pre-kickoff."""
    refs = refs.sort_values("Date").reset_index(drop=True)
    refs["card_gap"] = refs["away_card_pts"] - refs["home_card_pts"]
    refs["home_win"] = (refs["FTR"] == "H").astype(float)
    refs["pts_home"] = refs["FTR"].map({"H": 3, "D": 1, "A": 0}) / 3.0
    refs["pts_away"] = refs["FTR"].map({"H": 0, "D": 1, "A": 3}) / 3.0

    # Expanding league means (shifted — exclude current match)
    for col, name in [("FTHG", "lg_hg"), ("FTAG", "lg_ag"),
                      ("home_win", "lg_hw"), ("card_gap", "lg_card")]:
        refs[name] = refs[col].expanding().mean().shift(1)

    # Expanding per-ref means
    grp = refs.groupby("Referee")
    for col, name in [("FTHG", "ref_hg"), ("FTAG", "ref_ag"),
                      ("home_win", "ref_hw"), ("card_gap", "ref_card")]:
        refs[name] = grp[col].transform(lambda s: s.expanding().mean().shift(1))
    refs["ref_n"] = grp.cumcount()

    w = refs["ref_n"] / (refs["ref_n"] + k)
    refs["f_hg"] = (refs["ref_hg"] - refs["lg_hg"]).fillna(0) * w
    refs["f_ag"] = (refs["ref_ag"] - refs["lg_ag"]).fillna(0) * w
    refs["f_hw"] = (refs["ref_hw"] - refs["lg_hw"]).fillna(0) * w
    refs["f_card"] = (refs["ref_card"] - refs["lg_card"]).fillna(0) * w

    # Ref x team: team's prior pts rate with this ref minus with all other refs.
    # Long format: one row per (match, team).
    home = refs[["Date", "Referee", "HomeTeam", "pts_home"]].rename(
        columns={"HomeTeam": "team", "pts_home": "pts"})
    away = refs[["Date", "Referee", "AwayTeam", "pts_away"]].rename(
        columns={"AwayTeam": "team", "pts_away": "pts"})
    long = pd.concat([home, away]).sort_values("Date").reset_index(drop=True)
    by_rt = long.groupby(["Referee", "team"])["pts"]
    long["pts_with_ref"] = by_rt.transform(lambda s: s.expanding().mean().shift(1))
    long["n_with_ref"] = long.groupby(["Referee", "team"]).cumcount()
    by_t = long.groupby("team")["pts"]
    long["pts_all"] = by_t.transform(lambda s: s.expanding().mean().shift(1))
    wt = long["n_with_ref"] / (long["n_with_ref"] + k / 4)  # team pairs: smaller n, gentler k
    long["f_team"] = (long["pts_with_ref"] - long["pts_all"]).fillna(0) * wt

    fh = long.rename(columns={"team": "HomeTeam", "f_team": "f_team_h"})
    fa = long.rename(columns={"team": "AwayTeam", "f_team": "f_team_a"})
    refs = refs.merge(fh[["Date", "Referee", "HomeTeam", "f_team_h"]],
                      on=["Date", "Referee", "HomeTeam"], how="left")
    refs = refs.merge(fa[["Date", "Referee", "AwayTeam", "f_team_a"]],
                      on=["Date", "Referee", "AwayTeam"], how="left")

    feats = ["f_hg", "f_ag", "f_hw", "f_card", "f_team_h", "f_team_a"]
    refs[feats] = refs[feats].fillna(0)
    return refs[["Date", "HomeTeam", "AwayTeam"] + feats]


def rps3(p: np.ndarray, y: np.ndarray) -> float:
    o = np.zeros_like(p)
    o[np.arange(len(y)), y] = 1
    cp, co = np.cumsum(p, 1), np.cumsum(o, 1)
    return float((((cp - co) ** 2)[:, :2].sum(1) / 2).mean())


FEATS = ["f_hg", "f_ag", "f_hw", "f_card", "f_team_h", "f_team_a"]


def prepare(k: float) -> pd.DataFrame:
    res = pd.read_csv(CLV_CSV, parse_dates=["date"])
    refs = pd.read_csv(REFS_CSV, parse_dates=["Date"])
    feats = build_ref_features(refs, k)
    df = res.merge(feats, left_on=["date", "home", "away"],
                   right_on=["Date", "HomeTeam", "AwayTeam"], how="left")
    df[FEATS] = df[FEATS].fillna(0)

    m = pd.read_csv(MATCHES_CSV, parse_dates=["Date"])
    odds = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA"]
    df = df.merge(m[["Date", "HomeTeam", "AwayTeam"] + odds],
                  left_on=["date", "home", "away"],
                  right_on=["Date", "HomeTeam", "AwayTeam"], how="left")

    for c in ["p_home", "p_draw", "p_away"]:
        df[c] = df[c].clip(0.02, 0.96)
    df["lh"] = np.log(df["p_home"] / df["p_away"])
    df["ld"] = np.log(df["p_draw"] / df["p_away"])
    df["y"] = df["result"].map({"H": 0, "D": 1, "A": 2})
    return df


def walk_forward(df: pd.DataFrame):
    """Fit LR on earlier test seasons, predict later. Returns df with adjusted probs."""
    df = df.copy()
    for c in ["adj_h", "adj_d", "adj_a"]:
        df[c] = np.nan
    base_cols = ["lh", "ld"]
    for i, season in enumerate(TEST_ORDER):
        if i == 0:
            continue
        tr = df[df["season"].isin(TEST_ORDER[:i])].dropna(subset=base_cols + FEATS + ["y"])
        te_mask = df["season"] == season
        cols = base_cols + FEATS
        mu, sd = tr[cols].mean(), tr[cols].std().replace(0, 1)
        lr = LogisticRegression(C=1.0, max_iter=2000)
        lr.fit((tr[cols] - mu) / sd, tr["y"])
        p = lr.predict_proba((df.loc[te_mask, cols] - mu) / sd)
        df.loc[te_mask, ["adj_h", "adj_d", "adj_a"]] = p

        # baseline refit (same regularisation, no ref feats) for a fair comparison
        mu0, sd0 = tr[base_cols].mean(), tr[base_cols].std().replace(0, 1)
        lr0 = LogisticRegression(C=1.0, max_iter=2000)
        lr0.fit((tr[base_cols] - mu0) / sd0, tr["y"])
        p0 = lr0.predict_proba((df.loc[te_mask, base_cols] - mu0) / sd0)
        df.loc[te_mask, ["base_h", "base_d", "base_a"]] = p0
    return df.dropna(subset=["adj_h"])


def clv_roi(df: pd.DataFrame, pcols: list[str], thr: float, segment=None):
    """Flat-stake bets vs Pinnacle opening for the 3 outcomes; returns summary dict."""
    out = {"bets": 0, "clv": [], "pl": []}
    sides = [(pcols[0], "PSH", "PSCH", "H"), (pcols[1], "PSD", "PSCD", "D"),
             (pcols[2], "PSA", "PSCA", "A")]
    sub = df.dropna(subset=["PSH", "PSCH"])
    if segment is not None:
        sub = sub[segment.reindex(sub.index).fillna(False)]
    for pc, oc, cc, wins in sides:
        edge = sub[pc] * sub[oc] - 1.0
        sel = sub[edge >= thr]
        out["bets"] += len(sel)
        out["clv"] += list(sel[oc] / sel[cc] - 1.0)
        out["pl"] += list(np.where(sel["result"] == wins, sel[oc] - 1.0, -1.0))
    clv = np.array(out["clv"]); pl = np.array(out["pl"])
    return {"bets": out["bets"],
            "clv": clv.mean() if len(clv) else np.nan,
            "clv_pos": (clv > 0).mean() if len(clv) else np.nan,
            "roi": pl.mean() if len(pl) else np.nan}


def main():
    # choose k on the first walk-forward fold's TRAINING season only (2021/22 in-sample fit
    # quality of the ref features), to avoid picking k by test results
    print("=== shrinkage k selection (in-sample on 2021/22 only) ===")
    best_k, best_ll = None, np.inf
    for k in K_GRID:
        df = prepare(k)
        tr = df[df["season"] == "2021/22"].dropna(subset=["y"])
        cols = ["lh", "ld"] + FEATS
        mu, sd = tr[cols].mean(), tr[cols].std().replace(0, 1)
        lr = LogisticRegression(C=1.0, max_iter=2000)
        X = (tr[cols] - mu) / sd
        lr.fit(X, tr["y"])
        from sklearn.metrics import log_loss
        ll = log_loss(tr["y"], lr.predict_proba(X))
        print(f"  k={k}: train logloss {ll:.4f}")
        if ll < best_ll:
            best_k, best_ll = k, ll
    print(f"  -> using k={best_k}\n")

    df = prepare(best_k)
    wf = walk_forward(df)

    print("=== OUT-OF-SAMPLE RPS (2022/23–2024/25, walk-forward) ===")
    for season, g in wf.groupby("season"):
        y = g["y"].values.astype(int)
        r_adj = rps3(g[["adj_h", "adj_d", "adj_a"]].values, y)
        r_base = rps3(g[["base_h", "base_d", "base_a"]].values, y)
        r_raw = rps3(g[["p_home", "p_draw", "p_away"]].values
                     / g[["p_home", "p_draw", "p_away"]].values.sum(1, keepdims=True), y)
        print(f"  {season}: raw model {r_raw:.4f} | refit baseline {r_base:.4f} "
              f"| +ref feats {r_adj:.4f} ({r_adj - r_base:+.4f})")
    y = wf["y"].values.astype(int)
    print(f"  AGG (n={len(wf)}): refit baseline "
          f"{rps3(wf[['base_h','base_d','base_a']].values, y):.4f} | "
          f"+ref {rps3(wf[['adj_h','adj_d','adj_a']].values, y):.4f}")

    shift = (wf["adj_h"] - wf["base_h"]).abs()
    seg = shift >= DECISION_SHIFT
    print(f"\nmatches where ref feats moved home prob >= {DECISION_SHIFT:.1%}: "
          f"{seg.sum()} of {len(wf)} (median shift {shift.median():.4f})")

    print("\n=== CLV / ROI vs PINNACLE OPENING (flat 1u) ===")
    for thr in EDGE_THRESHOLDS:
        b = clv_roi(wf, ["base_h", "base_d", "base_a"], thr)
        a = clv_roi(wf, ["adj_h", "adj_d", "adj_a"], thr)
        print(f"  edge>={thr:.0%}:  base  {b['bets']:>4} bets  CLV {b['clv']:+.2%} "
              f"(pos {b['clv_pos']:.0%})  ROI {b['roi']:+.1%}")
        print(f"             +ref  {a['bets']:>4} bets  CLV {a['clv']:+.2%} "
              f"(pos {a['clv_pos']:.0%})  ROI {a['roi']:+.1%}")
        bs = clv_roi(wf, ["base_h", "base_d", "base_a"], thr, segment=seg)
        as_ = clv_roi(wf, ["adj_h", "adj_d", "adj_a"], thr, segment=seg)
        print(f"    changed-decision segment ({int(seg.sum())} matches): "
              f"base {bs['bets']} bets CLV {bs['clv']:+.2%} ROI {bs['roi']:+.1%} | "
              f"+ref {as_['bets']} bets CLV {as_['clv']:+.2%} ROI {as_['roi']:+.1%}")


if __name__ == "__main__":
    main()
