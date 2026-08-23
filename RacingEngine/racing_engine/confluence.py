"""Auditable, market-relative confidence layer for horse-racing prices.

Confluence does not create a fair price.  It records independent evidence that
the model may know something the market has underweighted.  Correlated signals
are first collapsed into an edge family, preventing ten variants of the same
track statistic from masquerading as ten independent edges.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp
from typing import Iterable


FAMILIES = (
    "horse_profile",
    "track_distance_going",
    "race_setup",
    "trainer_jockey",
    "environment",
)


@dataclass(frozen=True)
class EdgeEvidence:
    edge_id: str
    family: str
    direction: int
    strength: float
    reliability: float
    observed_at: str
    explanation: str
    source: str

    def validate(self, cutoff_at: str) -> None:
        if self.family not in FAMILIES:
            raise ValueError(f"unknown confluence family: {self.family}")
        if self.direction not in (-1, 0, 1):
            raise ValueError("direction must be -1, 0 or 1")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("strength must be between 0 and 1")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be between 0 and 1")
        if _instant(self.observed_at) > _instant(cutoff_at):
            raise ValueError(f"look-ahead evidence rejected: {self.edge_id}")


@dataclass(frozen=True)
class FamilyScore:
    family: str
    raw_score: float
    score: float
    evidence_count: int


@dataclass(frozen=True)
class ConfluenceCard:
    model_probability: float
    market_probability: float
    probability_edge: float
    market_disagreement: float
    net_score: float
    positive_families: int
    negative_families: int
    confidence_tier: str
    qualifies: bool
    family_scores: tuple[FamilyScore, ...]
    evidence: tuple[EdgeEvidence, ...]

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["family_scores"] = [asdict(item) for item in self.family_scores]
        value["evidence"] = [asdict(item) for item in self.evidence]
        return value


def score_confluence(
    *,
    model_probability: float,
    market_probability: float,
    evidence: Iterable[EdgeEvidence],
    cutoff_at: str,
    minimum_probability_edge: float = 0.02,
) -> ConfluenceCard:
    """Build a confidence card while keeping fair price and evidence separate."""
    if not 0.0 < model_probability < 1.0 or not 0.0 < market_probability < 1.0:
        raise ValueError("model and market probabilities must be between 0 and 1")
    items = tuple(evidence)
    grouped: dict[str, list[float]] = {family: [] for family in FAMILIES}
    for item in items:
        item.validate(cutoff_at)
        grouped[item.family].append(item.direction * item.strength * item.reliability)

    family_scores = tuple(
        FamilyScore(family, sum(values), _saturate(sum(values)), len(values))
        for family, values in grouped.items() if values
    )
    net = sum(item.score for item in family_scores)
    positive = sum(item.score >= 0.20 for item in family_scores)
    negative = sum(item.score <= -0.20 for item in family_scores)
    edge = model_probability - market_probability
    qualifies = edge >= minimum_probability_edge and positive >= 2 and negative == 0
    tier = _tier(net, positive, negative, qualifies)
    return ConfluenceCard(
        model_probability=model_probability,
        market_probability=market_probability,
        probability_edge=edge,
        market_disagreement=edge / market_probability,
        net_score=net,
        positive_families=positive,
        negative_families=negative,
        confidence_tier=tier,
        qualifies=qualifies,
        family_scores=family_scores,
        evidence=items,
    )


def _saturate(raw: float) -> float:
    """Bound a family to [-1, 1], strongly discounting correlated repeats."""
    if raw == 0:
        return 0.0
    return (1.0 if raw > 0 else -1.0) * (1.0 - exp(-abs(raw)))


def _tier(net: float, positive: int, negative: int, qualifies: bool) -> str:
    if not qualifies:
        return "PASS"
    if net >= 2.25 and positive >= 4:
        return "A"
    if net >= 1.45 and positive >= 3:
        return "B"
    return "C"


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
