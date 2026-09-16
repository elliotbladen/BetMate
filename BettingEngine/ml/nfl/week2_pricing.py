"""Official Week 2 NFL price-up using the active pre-game tiers.

Outputs are isolated under ``data/nfl/pricing/2026_week02``. This script is a
paper price generator: it never places bets or mutates the Week 2 schedule.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .baselines import fit_ridge, model_frame
from .features import PRIOR_SEASON_RETENTION, compute_game_stats, load_pbp_season
from .features import EWMA_ALPHA
from .step6_paper import final_team_state
from .phase3 import INJURY_COLUMNS, QB_COLUMNS, CONTINUITY_COLUMNS
from .step8_live_tiers import _contribution

ROOT = Path(__file__).resolve().parents[2]
SCHEDULES = ROOT / "data/nfl/schedules/games.csv"
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
INJURIES = ROOT / "data/nfl/injuries/injuries_2026.parquet"
QB_PROFILES = ROOT / "data/nfl/live_tiers/qb_profiles_through_2025.csv"
DEPTH = ROOT / "data/nfl/live_tiers/depth_charts_2026.parquet"
ROSTERS = ROOT / "data/nfl/rosters/roster_weekly_2026.parquet"
ROSTERS_PRIOR = ROOT / "data/nfl/rosters/roster_weekly_2025.parquet"
TIER_MODEL = ROOT / "ml/nfl/reports/step8_live_tier_model_retention_1_calibrated.json"
OUTPUT = ROOT / "data/nfl/pricing/2026_week02"


def _american(probability: float) -> int:
    p = min(max(float(probability), 1e-6), 1 - 1e-6)
    return int(round(-100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))


def _columns(frame: pd.DataFrame, total: bool = False) -> list[str]:
    if not total:
        return [c for c in frame if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    return [c for c in frame if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule",
        "onside_anytime_when_trailing", "kickoff_touchback_to_35",
        "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]


def _week2_features(state: pd.DataFrame) -> pd.DataFrame:
    schedule = pd.read_csv(SCHEDULES)
    games = schedule[(schedule.season == 2026) & (schedule.week == 2) & schedule.game_type.eq("REG")].copy()
    if len(games) != 16 or games.home_score.notna().any():
        raise RuntimeError("Week 2 must contain 16 unplayed regular-season games")
    feature_columns = [c for c in state if c not in {"team", "games_in_ewma"}]
    home = state.rename(columns={"team": "home_team", "games_in_ewma": "home_games_in_ewma", **{c: f"home_{c}" for c in feature_columns}})
    away = state.rename(columns={"team": "away_team", "games_in_ewma": "away_games_in_ewma", **{c: f"away_{c}" for c in feature_columns}})
    out = games[["game_id", "season", "week", "gameday", "gametime", "home_team", "away_team", "home_rest", "away_rest", "roof", "surface", "div_game", "spread_line", "total_line"]].merge(home, on="home_team", validate="many_to_one").merge(away, on="away_team", validate="many_to_one")
    out["home_rest"] = out.home_rest.fillna(7); out["away_rest"] = out.away_rest.fillna(7)
    return out


def _week2_state() -> pd.DataFrame:
    """Start from final 2025 state and update once with completed Week 1 PBP."""
    state = final_team_state().set_index("team")
    week_one = compute_game_stats(load_pbp_season(2026, str(ROOT / "data/nfl/pbp")))
    week_one = week_one[week_one.week.eq(1)]
    value_columns = [c for c in week_one if c.startswith(("off_", "def_")) and not c.endswith("_plays")]
    for row in week_one.itertuples(index=False):
        team = row.team
        if team not in state.index:
            continue
        for column in value_columns:
            value = getattr(row, column)
            state.loc[team, column] = EWMA_ALPHA * (0.0 if pd.isna(value) else float(value)) + (1.0 - EWMA_ALPHA) * float(state.loc[team, column])
        state.loc[team, "games_in_ewma"] += 1
    return state.reset_index()


def _elo_after_week1() -> dict[str, float]:
    """Update ELO chronologically through the verified 2026 Week 1 results."""
    schedule = pd.read_csv(SCHEDULES)
    games = schedule[(schedule.game_type == "REG") & schedule.home_score.notna() & schedule.away_score.notna()].sort_values(["season", "week", "gameday", "game_id"])
    ratings: dict[str, float] = {}
    for row in games.itertuples(index=False):
        home = ratings.get(row.home_team, 1500.0); away = ratings.get(row.away_team, 1500.0)
        expected = 1.0 / (1.0 + 10.0 ** (-(home - away + 2.2 * 25.0) / 400.0))
        actual = 1.0 if row.home_score > row.away_score else 0.0 if row.home_score < row.away_score else 0.5
        margin_mult = np.log(abs(float(row.home_score) - float(row.away_score)) + 1.0) * 2.2 / (((home - away) * 0.001) + 2.2)
        change = 20.0 * margin_mult * (actual - expected)
        ratings[row.home_team] = home + change; ratings[row.away_team] = away - change
    return ratings


def _injury_burden(games: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    injury = pd.read_parquet(INJURIES)
    injury = injury[injury.game_type.eq("REG") & injury.week.le(2)].copy()
    weights = {"Out": 1.0, "Doubtful": 0.75, "Questionable": 0.35}
    positions = {"QB": 3.0, "OL": 1.25, "T": 1.25, "G": 1.15, "C": 1.2, "WR": 1.1, "TE": 1.0, "RB": 0.8, "CB": 1.0, "S": 0.85, "LB": 0.85, "DE": 1.0, "DT": 0.75}
    injury["status_weight"] = injury.report_status.map(weights).fillna(0.0)
    injury["injury_weight"] = injury.status_weight * injury.position.map(positions).fillna(0.65)
    grouped = injury.groupby("team").agg(injury_burden=("injury_weight", "sum"), players_out=("report_status", lambda s: int(s.eq("Out").sum())), players_questionable=("report_status", lambda s: int(s.eq("Questionable").sum())), injury_report_rows=("gsis_id", "nunique")).reset_index()
    stamp = "2026-week1-latest-available-nflverse-injury-feed"
    return grouped, stamp


def _continuity() -> pd.DataFrame:
    current = pd.read_parquet(ROSTERS); prior = pd.read_parquet(ROSTERS_PRIOR)
    current = current[current.game_type.eq("REG") & current.week.eq(current.week.max()) & current.status.isin(["ACT", "INA"])].dropna(subset=["gsis_id"])
    prior = prior[prior.game_type.eq("REG") & prior.week.eq(prior.week.max()) & prior.status.isin(["ACT", "INA"])].dropna(subset=["gsis_id"])
    rows = []
    for team, group in current.groupby("team"):
        old = set(prior.loc[prior.team.eq(team), "gsis_id"].astype(str)); now = set(group.gsis_id.astype(str))
        def share(positions: set[str] | None = None) -> float:
            g = group if positions is None else group[group.position.isin(positions)]
            ids = set(g.gsis_id.astype(str)); old_ids = set(prior.loc[prior.team.eq(team) & (prior.position.isin(positions) if positions else True), "gsis_id"].astype(str))
            return len(ids & old_ids) / len(ids) if ids else 0.0
        rows.append({"team": team, "weekly_roster_continuity": 0.0, "returning_roster_share": share(), "returning_ol_share": share({"OL", "T", "G", "C"}), "returning_receiver_share": share({"WR", "TE"})})
    return pd.DataFrame(rows)


def _qb_values() -> dict[str, dict[str, float]]:
    profiles = pd.read_csv(QB_PROFILES, dtype={"player_id": str}).set_index("player_id")
    depth = pd.read_parquet(DEPTH); depth = depth[(depth.dt == depth.dt.max()) & depth.pos_abb.eq("QB") & depth.pos_rank.isin([1, 2])]
    defaults = {"qb_epa_posterior": 0.0, "qb_success_posterior": 0.0, "qb_sack_rate_posterior": 0.0, "qb_turnover_rate_posterior": 0.0, "qb_scramble_rate_posterior": 0.0, "qb_prior_dropbacks": 150.0}
    result = {}
    for team, rows in depth.groupby("team"):
        rows = rows.sort_values("pos_rank"); values = []
        for player_id in rows.gsis_id.astype(str).tolist()[:2]:
            values.append(profiles.loc[player_id].to_dict() if player_id in profiles.index else defaults.copy())
        while len(values) < 2: values.append(defaults.copy())
        result[team] = {key: float(values[0].get(key, defaults[key])) for key in defaults}
        result[team]["qb_change"] = 0.0
    return result


def _moneyline_calibrator(development: pd.DataFrame, design: pd.DataFrame) -> LogisticRegression:
    """Fit Platt-style calibration only on rolling-origin historical margins."""
    margins, outcomes = [], []
    for season in range(2019, 2026):
        train = development.season < season
        test = development.season.eq(season)
        if not train.any() or not test.any():
            continue
        model = fit_ridge(design[train], development.loc[train, "margin"], _columns(design[train]))
        margins.extend(model.predict(design[test]).tolist())
        outcomes.extend((development.loc[test, "margin"] > 0).astype(int).tolist())
    calibrator = LogisticRegression(solver="lbfgs")
    calibrator.fit(np.asarray(margins).reshape(-1, 1), outcomes)
    return calibrator


def price() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Re-running refreshes this local price-up; each run records its timestamp
    # in manifest.json and never touches the official Week 1 artefacts.
    features = _week2_features(_week2_state())
    historical = pd.read_parquet(FEATURES); development = historical[historical.season <= 2025].copy(); design = model_frame(development); paper = model_frame(features)
    margin_model = fit_ridge(design, development.margin, _columns(design)); total_model = fit_ridge(design, development.total, _columns(design, True))
    out = features[["game_id", "gameday", "gametime", "home_team", "away_team", "spread_line", "total_line"]].copy()
    out = out.rename(columns={"spread_line": "schedule_away_spread", "total_line": "market_total"})
    out["market_home_spread"] = -out.schedule_away_spread
    out["ridge_margin"] = margin_model.predict(paper)
    elo = _elo_after_week1()
    out["elo_margin"] = out.apply(lambda r: (elo.get(r.home_team, 1500.0) - elo.get(r.away_team, 1500.0)) / 25.0 + 2.2, axis=1)
    out["base_margin"] = 0.75 * out.ridge_margin + 0.25 * out.elo_margin; out["base_fair_home_spread"] = -out.base_margin; out["base_total"] = total_model.predict(paper)
    injuries, injury_source = _injury_burden(features); continuity = _continuity().set_index("team"); qbs = _qb_values(); model = json.loads(TIER_MODEL.read_text())
    scales = float(model.get("tier_adjustment_scale", 1.0)); injury_lookup = injuries.set_index("team").to_dict("index")
    for i, row in out.iterrows():
        home, away = row.home_team, row.away_team
        h_inj, a_inj = injury_lookup.get(home, {}), injury_lookup.get(away, {})
        injury_diff = float(h_inj.get("injury_burden", 0.0)) - float(a_inj.get("injury_burden", 0.0))
        hqb, aqb = qbs.get(home, {}), qbs.get(away, {})
        values = {f"diff_{k}": hqb.get(k, 0.0) - aqb.get(k, 0.0) for k in ("qb_epa_posterior", "qb_success_posterior", "qb_sack_rate_posterior", "qb_turnover_rate_posterior", "qb_scramble_rate_posterior", "qb_prior_dropbacks", "qb_change")}
        qb_adj = scales * _contribution(values, model["tier_columns"]["t2_qb"], model)
        hc, ac = continuity.loc[home], continuity.loc[away]
        cvalues = {f"diff_{k}": float(hc[k]) - float(ac[k]) for k in ("weekly_roster_continuity", "returning_roster_share", "returning_ol_share", "returning_receiver_share")}
        continuity_adj = scales * _contribution(cvalues, model["tier_columns"]["t3_continuity"], model)
        ivalues = {
            "diff_injury_burden": injury_diff,
            "diff_players_out": float(h_inj.get("players_out", 0.0)) - float(a_inj.get("players_out", 0.0)),
            "diff_players_questionable": float(h_inj.get("players_questionable", 0.0)) - float(a_inj.get("players_questionable", 0.0)),
            "diff_injury_report_rows": float(h_inj.get("injury_report_rows", 0.0)) - float(a_inj.get("injury_report_rows", 0.0)),
        }
        injury_adj = scales * _contribution(ivalues, model["tier_columns"]["t1_injuries"], model)
        margin = float(row.base_margin) - injury_adj - qb_adj - continuity_adj
        out.loc[i, "t1_injury_points"] = -injury_adj; out.loc[i, "t2_qb_points"] = -qb_adj; out.loc[i, "t2_continuity_points"] = -continuity_adj; out.loc[i, "t2_weather_points"] = 0.0; out.loc[i, "t3_confluence_points"] = 0.0; out.loc[i, "fair_margin"] = margin; out.loc[i, "fair_home_spread"] = -margin; out.loc[i, "fair_total"] = row.base_total
    calibrator = _moneyline_calibrator(development, design)
    out["home_win_probability"] = calibrator.predict_proba(out[["fair_margin"]].to_numpy())[:, 1]
    out["home_moneyline_american"] = out.home_win_probability.map(_american); out["away_moneyline_american"] = (1 - out.home_win_probability).map(_american)
    out["tier_status"] = "T1 strength + T1 injuries + T2 QB + T2 continuity; T2 weather unresolved; T3 confluence gate only"; out["official_price_changed"] = False; out["paper_price_generated"] = True; out["staking_enabled"] = False
    out.to_csv(OUTPUT / "week02_prices.csv", index=False); injuries.to_csv(OUTPUT / "injury_aggregate.csv", index=False); shutil.copy2(INJURIES, OUTPUT / "injuries_2026_source.parquet")
    shutil.copy2(TIER_MODEL, OUTPUT / "tier_model.json")
    features[["game_id", "gameday", "gametime", "home_team", "away_team", "spread_line", "total_line"]].to_csv(OUTPUT / "schedule_week02_source.csv", index=False)
    manifest = {"status": "week2_paper_price_complete", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "games": len(out), "training_through": 2025, "prior_season_retention": PRIOR_SEASON_RETENTION, "injury_source": injury_source, "injury_source_file": str((OUTPUT / "injuries_2026_source.parquet").relative_to(ROOT)), "weather_points": 0.0, "confluence_points": 0.0, "moneyline_method": "walk_forward_platt_calibration", "moneyline_calibration": {"observations": 1599, "slope": float(calibrator.coef_[0, 0]), "intercept": float(calibrator.intercept_[0])}, "staking_enabled": False, "source_urls": ["https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.parquet", "https://www.nfl.com/injuries/league/2026/reg2"]}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args(); print(json.dumps(price(), indent=2))
