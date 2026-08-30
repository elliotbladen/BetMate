"""Point-in-time NFL quarterback and roster-continuity features."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .data_contract import schedule_team_code


QB_PRIOR_DROPBACKS = 150.0
ACTIVE_ROSTER_STATUSES = frozenset({"ACT", "INA"})
INJURY_STATUS_WEIGHT = {"Out": 1.0, "Doubtful": 0.75, "Questionable": 0.35}
POSITION_WEIGHT = {
    "QB": 3.0, "OL": 1.25, "T": 1.25, "G": 1.15, "C": 1.2,
    "WR": 1.1, "TE": 1.0, "RB": 0.8, "CB": 1.0, "S": 0.85,
    "LB": 0.85, "DE": 1.0, "DT": 0.75,
}


def starter_mixture(starter_value: float, backup_value: float, starter_probability: float) -> float:
    """Price an uncertain starter without pretending the status is certain."""
    probability = float(starter_probability)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("starter_probability must be between zero and one")
    return probability * float(starter_value) + (1.0 - probability) * float(backup_value)


def load_qb_game_stats(pbp_dir: str, seasons: range) -> pd.DataFrame:
    rows = []
    columns = [
        "game_id", "season", "week", "posteam", "passer_player_id",
        "epa", "success", "qb_dropback", "pass_attempt", "sack",
        "interception", "qb_scramble",
    ]
    for season in seasons:
        data = pd.read_parquet(Path(pbp_dir) / f"play_by_play_{season}.parquet", columns=columns)
        data = data[data.qb_dropback.fillna(0).eq(1) & data.passer_player_id.notna()].copy()
        data["posteam"] = data.posteam.map(
            lambda team: schedule_team_code(team, season) if pd.notna(team) else team
        )
        grouped = data.groupby(["game_id", "season", "week", "posteam", "passer_player_id"])
        result = grouped.agg(
            dropbacks=("qb_dropback", "sum"),
            qb_epa_sum=("epa", "sum"),
            qb_successes=("success", "sum"),
            sacks=("sack", "sum"),
            interceptions=("interception", "sum"),
            scrambles=("qb_scramble", "sum"),
        ).reset_index()
        rows.append(result)
    return pd.concat(rows, ignore_index=True)


def build_qb_features(schedules: pd.DataFrame, qb_games: pd.DataFrame) -> pd.DataFrame:
    """Emit each starter's posterior before updating it with the current game."""
    lookup = {
        (row.game_id, row.passer_player_id): row
        for row in qb_games.itertuples(index=False)
    }
    state = defaultdict(lambda: {"dropbacks": 0.0, "epa": 0.0, "success": 0.0,
                                 "sacks": 0.0, "ints": 0.0, "scrambles": 0.0})
    previous_starter: dict[str, str] = {}
    rows = []
    regular = schedules[schedules.game_type.eq("REG")].sort_values(["gameday", "game_id"])
    for game in regular.itertuples(index=False):
        row = {"game_id": game.game_id}
        for side in ("home", "away"):
            team = getattr(game, f"{side}_team")
            player = getattr(game, f"{side}_qb_id")
            player = "" if pd.isna(player) else str(player)
            values = state[player]
            denominator = values["dropbacks"] + QB_PRIOR_DROPBACKS
            row[f"{side}_qb_id"] = player
            row[f"{side}_qb_epa_posterior"] = values["epa"] / denominator
            row[f"{side}_qb_success_posterior"] = values["success"] / denominator
            row[f"{side}_qb_sack_rate_posterior"] = values["sacks"] / denominator
            row[f"{side}_qb_turnover_rate_posterior"] = values["ints"] / denominator
            row[f"{side}_qb_scramble_rate_posterior"] = values["scrambles"] / denominator
            row[f"{side}_qb_prior_dropbacks"] = values["dropbacks"]
            prior = previous_starter.get(team)
            row[f"{side}_qb_change"] = int(bool(prior) and bool(player) and prior != player)
        for metric in (
            "qb_epa_posterior", "qb_success_posterior", "qb_sack_rate_posterior",
            "qb_turnover_rate_posterior", "qb_scramble_rate_posterior",
            "qb_prior_dropbacks", "qb_change",
        ):
            row[f"diff_{metric}"] = row[f"home_{metric}"] - row[f"away_{metric}"]
        rows.append(row)
        for side in ("home", "away"):
            team = getattr(game, f"{side}_team")
            player = row[f"{side}_qb_id"]
            if player:
                previous_starter[team] = player
                played = lookup.get((game.game_id, player))
                if played is not None:
                    values = state[player]
                    values["dropbacks"] += float(played.dropbacks)
                    values["epa"] += float(played.qb_epa_sum)
                    values["success"] += float(played.qb_successes)
                    values["sacks"] += float(played.sacks)
                    values["ints"] += float(played.interceptions)
                    values["scrambles"] += float(played.scrambles)
    return pd.DataFrame(rows)


def build_roster_continuity(roster_dir: str) -> pd.DataFrame:
    files = sorted(Path(roster_dir).glob("roster_weekly_*.parquet"))
    columns = ["season", "week", "team", "position", "status", "gsis_id", "game_type"]
    roster = pd.concat([pd.read_parquet(path, columns=columns) for path in files], ignore_index=True)
    roster = roster[roster.game_type.eq("REG") & roster.status.isin(ACTIVE_ROSTER_STATUSES)]
    roster = roster.dropna(subset=["gsis_id"]).drop_duplicates(["season", "week", "team", "gsis_id"])
    sets = {
        (int(season), int(week), team): set(group.gsis_id.astype(str))
        for (season, week, team), group in roster.groupby(["season", "week", "team"])
    }
    unit_sets = {
        (int(season), int(week), team, unit): set(group.gsis_id.astype(str))
        for (season, week, team, unit), group in roster.assign(
            unit=np.where(roster.position.eq("OL"), "ol",
                 np.where(roster.position.isin(["WR", "TE"]), "receiver", "other"))
        ).groupby(["season", "week", "team", "unit"])
    }
    final_week = roster.groupby(["season", "team"]).week.max().to_dict()
    rows = []
    for (season, week, team), current in sorted(sets.items()):
        prior_week = sets.get((season, week - 1, team), set())
        prior_season_week = final_week.get((season - 1, team))
        prior_season = sets.get((season - 1, prior_season_week, team), set()) if prior_season_week else set()
        row = {
            "season": season, "week": week, "team": team,
            "weekly_roster_continuity": len(current & prior_week) / len(current) if prior_week else np.nan,
            "returning_roster_share": len(current & prior_season) / len(current) if prior_season else np.nan,
            "active_roster_count": len(current),
        }
        for unit in ("ol", "receiver"):
            current_unit = unit_sets.get((season, week, team, unit), set())
            prior_unit = unit_sets.get((season - 1, prior_season_week, team, unit), set()) if prior_season_week else set()
            row[f"returning_{unit}_share"] = (
                len(current_unit & prior_unit) / len(current_unit) if current_unit and prior_unit else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def build_injury_burden(injury_dir: str, schedules: pd.DataFrame) -> pd.DataFrame:
    """Position-weight final reports, excluding records modified after gameday."""
    files = sorted(Path(injury_dir).glob("injuries_*.parquet"))
    injuries = pd.concat([pd.read_parquet(path) for path in files], ignore_index=True)
    injuries = injuries[injuries.game_type.eq("REG")].copy()
    injuries["date_modified"] = pd.to_datetime(injuries.date_modified, utc=True, errors="coerce")
    game_dates = schedules[schedules.game_type.eq("REG")][
        ["season", "week", "home_team", "away_team", "gameday"]
    ].copy()
    home = game_dates.rename(columns={"home_team": "team"}).drop(columns="away_team")
    away = game_dates.rename(columns={"away_team": "team"}).drop(columns="home_team")
    dates = pd.concat([home, away], ignore_index=True).drop_duplicates(["season", "week", "team"])
    dates["gameday"] = pd.to_datetime(dates.gameday, utc=True, errors="coerce")
    injuries = injuries.merge(dates, on=["season", "week", "team"], how="inner", validate="many_to_one")
    # A date-only schedule cannot safely order same-day revisions. Retain them
    # as weekly pre-game reports but reject anything from a later calendar day.
    injuries = injuries[
        injuries.date_modified.isna() |
        (injuries.date_modified.dt.date <= injuries.gameday.dt.date)
    ].copy()
    injuries["status_weight"] = injuries.report_status.map(INJURY_STATUS_WEIGHT).fillna(0.0)
    injuries["position_weight"] = injuries.position.map(POSITION_WEIGHT).fillna(0.65)
    injuries["injury_weight"] = injuries.status_weight * injuries.position_weight
    injuries["out_player"] = injuries.report_status.eq("Out").astype(int)
    injuries["questionable_player"] = injuries.report_status.eq("Questionable").astype(int)
    return injuries.groupby(["season", "week", "team"], as_index=False).agg(
        injury_burden=("injury_weight", "sum"),
        players_out=("out_player", "sum"),
        players_questionable=("questionable_player", "sum"),
        injury_report_rows=("gsis_id", "nunique"),
        latest_injury_update=("date_modified", "max"),
    )


def build_personnel_store(
    schedules_path: str = "data/nfl/schedules/games.csv",
    pbp_dir: str = "data/nfl/pbp",
    roster_dir: str = "data/nfl/rosters",
    injury_dir: str = "data/nfl/injuries",
    output_path: str = "data/nfl/features/personnel_context.parquet",
) -> pd.DataFrame:
    schedules = pd.read_csv(schedules_path)
    schedules = schedules[schedules.season.between(2014, 2025)].copy()
    qb_games = load_qb_game_stats(pbp_dir, range(2014, 2026))
    qb = build_qb_features(schedules, qb_games)
    continuity = build_roster_continuity(roster_dir)
    injuries = build_injury_burden(injury_dir, schedules)
    continuity = continuity.merge(injuries, on=["season", "week", "team"], how="left", validate="one_to_one")
    home = continuity.add_prefix("home_").rename(columns={"home_season": "season", "home_week": "week"})
    away = continuity.add_prefix("away_").rename(columns={"away_season": "season", "away_week": "week"})
    games = schedules[schedules.game_type.eq("REG")][[
        "game_id", "season", "week", "home_team", "away_team", "temp", "wind", "roof", "surface",
    ]].copy()
    games = games.merge(qb, on="game_id", how="left", validate="one_to_one")
    games = games.merge(home, left_on=["season", "week", "home_team"],
                        right_on=["season", "week", "home_team"], how="left", validate="many_to_one")
    games = games.merge(away, left_on=["season", "week", "away_team"],
                        right_on=["season", "week", "away_team"], how="left", validate="many_to_one")
    for metric in ("weekly_roster_continuity", "returning_roster_share",
                   "returning_ol_share", "returning_receiver_share", "active_roster_count",
                   "injury_burden", "players_out", "players_questionable", "injury_report_rows"):
        games[f"diff_{metric}"] = games[f"home_{metric}"] - games[f"away_{metric}"]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    games.to_parquet(output, index=False)
    return games


if __name__ == "__main__":
    store = build_personnel_store()
    print(f"saved {len(store)} rows; QB coverage={store.home_qb_id.ne('').mean():.3%}")
