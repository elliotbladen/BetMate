"""Conservative extraction of official steward-report evidence.

The parser intentionally produces explainable categories, not an LLM opinion.
Its provisional trip figures are stored for research and review only; V1 ratings
do not consume them.  They can enter a future model only after chronological
validation against subsequent performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re

from .ratings import horse_key


PARSER_VERSION = "stewards-rule-v1.0"
REPORT_SOURCE = "racing-com-stewards-authorised"


@dataclass(frozen=True)
class EventRule:
    category: str
    severity: str
    trip_adjustment: float = 0.0
    fitness_status: str | None = None
    requires_review: bool = False
    patterns: tuple[str, ...] = ()


# These are deliberately conservative *rating points / length equivalents*.
# A raw report alone cannot establish the precise cost of an incident.  Wide
# passages are retained as evidence but receive no automatic adjustment until
# distance travelled and sectional confirmation are available.
RULES = (
    EventRule("severe_interference", "severe", 1.50, requires_review=True,
              patterns=(r"badly checked", r"checked .*avoid", r"lost .*rightful running", r"badly hampered", r"heavily (?:bumped|crowded)")),
    EventRule("held_up", "severe", 0.75, requires_review=True,
              patterns=(r"unable to be (?:fully )?tested", r"remained held up", r"held up .* until .* (?:100|50)m")),
    EventRule("interference", "moderate", 0.50,
              patterns=(r"\bhampered\b", r"\bcrowded\b", r"\bsteadied\b", r"\bchecked\b", r"\bbumped\b")),
    EventRule("held_up", "moderate", 0.50,
              patterns=(r"\bheld up\b", r"difficulty obtaining clear running", r"disappointed for clear running")),
    EventRule("slow_start", "moderate", 0.50,
              patterns=(r"slow to begin", r"lost ground (?:at|on) (?:the )?start", r"began awkwardly")),
    EventRule("wide_no_cover", "moderate", 0.0,
              patterns=(r"wide,? without cover", r"very wide,? without cover", r"raced three wide")),
    EventRule("overraced", "mild", 0.0,
              patterns=(r"raced keenly", r"over-raced", r"pulled hard")),
    EventRule("gait_or_direction", "mild", 0.0,
              patterns=(r"laid (?:in|out)", r"hung (?:in|out)", r"did not stretch out")),
    EventRule("vet_material", "material", 0.0, "material", True,
              patterns=(r"\bbled\b", r"\blame\b", r"\binjur", r"tendon", r"suspensory", r"fracture", r"shin sore", r"respiratory", r"slow to recover", r"vet(?:erinary)? clearance", r"stand down")),
    EventRule("vet_clear", "clear", 0.0, "cleared", False,
              patterns=(r"did not (?:reveal|identify) (?:any )?(?:significant )?abnormal", r"no significant abnormal", r"passed fit to start")),
)


def plain_text(html: str) -> str:
    """Make source HTML readable while preserving paragraph boundaries."""
    text = re.sub(r"(?i)</p\s*>", "\n", html or "")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t\r\n]+", " ", unescape(text)).strip()


def _paragraphs(html: str) -> list[str]:
    parts = re.findall(r"(?is)<p[^>]*>(.*?)</p>", html or "")
    return [plain_text(part) for part in parts if plain_text(part)]


def _normalised(text: str) -> str:
    text = re.sub(r"\([^)]*\)", "", text or "")
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _horse_for_paragraph(paragraph: str, horse_names: list[str]) -> str | None:
    compact = _normalised(paragraph)
    # Longest-first avoids choosing a shorter name embedded within another.
    for name in sorted(horse_names, key=lambda value: len(_normalised(value)), reverse=True):
        key = _normalised(name)
        if key and compact.startswith(key):
            return name
    return None


def classify_report(html: str, horse_names: list[str]) -> list[dict]:
    """Return source-linked classifications for identifiable runner paragraphs."""
    events: list[dict] = []
    for paragraph_index, paragraph in enumerate(_paragraphs(html)):
        horse = _horse_for_paragraph(paragraph, horse_names)
        if not horse:
            continue
        lowered = paragraph.lower()
        # A clear vet report is useful context but never cancels an actual
        # material condition mentioned elsewhere in the same paragraph.
        matching = [rule for rule in RULES if any(re.search(pattern, lowered) for pattern in rule.patterns)]
        if any(rule.category == "vet_material" for rule in matching):
            matching = [rule for rule in matching if rule.category != "vet_clear"]
        # One paragraph may match both the severe and generic variants of the
        # same event.  Retain only the strongest classification; otherwise a
        # held-up run could be double-counted downstream.
        severity_rank = {"clear": 0, "mild": 1, "moderate": 2, "severe": 3, "material": 4}
        strongest: dict[str, EventRule] = {}
        for rule in matching:
            current = strongest.get(rule.category)
            if current is None or severity_rank[rule.severity] > severity_rank[current.severity]:
                strongest[rule.category] = rule
        matching = list(strongest.values())
        for rule in matching:
            events.append({
                "event_key": f"{paragraph_index}:{rule.category}",
                "horse_key": horse_key(horse),
                "horse_name": horse,
                "category": rule.category,
                "severity": rule.severity,
                "parser_confidence": 0.95,
                "suggested_trip_adjustment": rule.trip_adjustment,
                "fitness_status": rule.fitness_status,
                "requires_human_review": rule.requires_review,
                "evidence_text": paragraph,
            })
    return events
