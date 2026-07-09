"""
League configuration loader — one engine, N league configs.

Each league is a YAML file in ml/football/leagues/. The config carries every
constant that differs between leagues (data sources, model constants, Elo
parameters, tier coefficients) so the model code itself stays league-agnostic.

Usage:
    from ml.football.league_config import load_league
    cfg = load_league("epl")
    cfg.matches_csv          # absolute Path
    cfg.model["rho"]         # -0.13
    cfg.tier_params          # TierParams for models.tiers.apply_all_tiers
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_FOOTBALL_ROOT = Path(__file__).parent
LEAGUES_DIR    = _FOOTBALL_ROOT / "leagues"
DATA_ROOT      = _FOOTBALL_ROOT / "data"


@dataclass(frozen=True)
class LeagueConfig:
    key: str
    name: str
    raw: dict

    # ── data paths (absolute) ────────────────────────────────────────────────
    @property
    def data_dir(self) -> Path:
        return DATA_ROOT / self.key

    @property
    def matches_csv(self) -> Path:
        return self.data_dir / self.raw["data"]["matches_csv"]

    @property
    def xg_csv(self) -> Path | None:
        rel = self.raw["data"].get("xg_csv")
        return (self.data_dir / rel) if rel else None

    @property
    def ppda_csv(self) -> Path | None:
        rel = self.raw["data"].get("ppda_csv")
        return (self.data_dir / rel) if rel else None

    @property
    def clv_dir(self) -> Path:
        return self.data_dir / self.raw["data"].get("clv_dir", "clv")

    @property
    def results_csv(self) -> Path:
        return self.clv_dir / "backtest_results.csv"

    @property
    def xg_fallback_factor(self) -> float:
        return float(self.raw["data"].get("xg_fallback_factor", 0.85))

    @property
    def goals_fed(self) -> bool:
        """True when the league has no xG source — D-C fits on goals."""
        return self.raw["data"].get("xg_csv") is None

    # ── model / elo / backtest blocks ────────────────────────────────────────
    @property
    def model(self) -> dict:
        return self.raw["model"]

    @property
    def elo(self) -> dict:
        return self.raw["elo"]

    @property
    def test_seasons(self) -> list[str]:
        return list(self.raw["backtest"]["test_seasons"])

    @property
    def feature_seasons(self) -> list[str]:
        return list(self.raw["backtest"]["feature_seasons"])

    # ── tiers ────────────────────────────────────────────────────────────────
    @property
    def tier_params(self):
        # Imported lazily to avoid a circular import at module load
        from ml.football.models.tiers import TierParams
        t = self.raw["tiers"]
        return TierParams(
            league_ppda_sum=float(t["league_ppda_sum"]),
            league_ref_goals=float(t["league_ref_goals"]),
            short_rest_days=int(t["short_rest_days"]),
            fatigue_factor=float(t["fatigue_factor"]),
            corners_home_avg=float(t["corners_home_avg"]),
            corners_away_avg=float(t["corners_away_avg"]),
            sp_xg_per_corner=float(t["sp_xg_per_corner"]),
            sp_weight=float(t["sp_weight"]),
            sp_cap=float(t["sp_cap"]),
            ppda_goals_coef=float(t["ppda_goals_coef"]),
            form_goals_coef=float(t["form_goals_coef"]),
            ref_goals_coef=float(t["ref_goals_coef"]),
        )


def load_league(key: str) -> LeagueConfig:
    path = LEAGUES_DIR / f"{key}.yaml"
    if not path.exists():
        known = sorted(p.stem for p in LEAGUES_DIR.glob("*.yaml"))
        raise FileNotFoundError(f"No league config '{key}'. Known leagues: {known}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return LeagueConfig(key=raw["key"], name=raw["name"], raw=raw)
