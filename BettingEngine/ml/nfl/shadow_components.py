"""Contracts for the next NFL shadow-model components.

This module deliberately contains no official-price changes and no fitted
coefficients.  It defines the four research tracks, their target markets,
point-in-time feature boundaries and maximum future overlay size.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Market = Literal["margin", "total"]


@dataclass(frozen=True)
class ShadowComponent:
    name: str
    target_market: Market
    feature_families: tuple[str, ...]
    cap_points: float
    status: str = "shadow_only"


SHADOW_COMPONENTS: tuple[ShadowComponent, ...] = (
    ShadowComponent(
        "drive_red_zone_residual",
        "total",
        ("drives", "field_position", "red_zone_opportunity", "goal_to_go"),
        3.0,
    ),
    ShadowComponent(
        "bayesian_touchdown_field_goal_regression",
        "total",
        ("red_zone_opportunity", "touchdown_rate", "field_goal_rate", "league_prior"),
        3.0,
    ),
    ShadowComponent(
        "turnover_luck_residual",
        "margin",
        ("interception_rate", "fumble_rate", "pressure", "expected_turnover_rate"),
        1.5,
    ),
    ShadowComponent(
        "special_teams_field_position",
        "margin",
        ("punt_field_position", "kickoff_field_position", "field_goal_distance", "return_epa"),
        1.5,
    ),
)


def component_names() -> tuple[str, ...]:
    return tuple(component.name for component in SHADOW_COMPONENTS)


def validate_shadow_components() -> None:
    """Fail if a component contract could silently double-count another one."""
    names = component_names()
    if len(names) != len(set(names)):
        raise ValueError("duplicate shadow component name")
    for component in SHADOW_COMPONENTS:
        if component.cap_points <= 0:
            raise ValueError(f"{component.name} must have a positive research cap")
        if not component.feature_families:
            raise ValueError(f"{component.name} has no feature families")


def apply_research_caps(base: float, increments: dict[str, float]) -> float:
    """Return a capped shadow value; never used by the official price path."""
    validate_shadow_components()
    by_name = {component.name: component for component in SHADOW_COMPONENTS}
    total = 0.0
    for name, increment in increments.items():
        if name not in by_name:
            raise KeyError(f"unknown shadow component: {name}")
        cap = by_name[name].cap_points
        total += max(-cap, min(cap, float(increment)))
    return float(base + total)
