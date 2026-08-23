"""Official Australian flat-race WFA schedule (AR 168/169, 1 June 2026)."""
from __future__ import annotations

from datetime import date

from .horse_profiles import FEMALE_SEXES, normalise_sex

RULES_SOURCE = "Australian Rules of Racing, 1 June 2026, AR 168-170"
MONTH_INDEX = {month: index for index, month in enumerate((8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7))}

# Distance band, then age. None means the age is not provided/eligible that month.
SCHEDULE = {
    (1000, 1200): {2: [None,None,None,None,None,45,46,47,48,49,50,51], 3: [51.5,52,53,53.5,54.5,55,55.5,56,56.5,57,57.5,58], 4: [58.5]*12, 5: [58.5]*12},
    (1201, 1400): {2: [None,None,None,None,None,44,45,46,47,48,49,50], 3: [50.5,51,52,53,54,54.5,55.5,56,56.5,57,57.5,58], 4: [58.5,58.5,58.5]+[59]*9, 5: [59]*12},
    (1401, 1600): {2: [None,None,None,None,None,43.5,44.5,45.5,46.5,47.5,48.5,49.5], 3: [50,50.5,51,52,53,54,55,56,56.5,57,57.5,58], 4: [58.5,58.5,58.5]+[59]*9, 5: [59]*12},
    (1601, 2000): {2: [None,None,None,None,None,42.5,43.5,44.5,45.5,46.5,47.5,48.5], 3: [49,49.5,50,51,52,53,54,54.5,55.5,56.5,57,57.5], 4: [58,58,58,58.5,58.5,58.5]+[59]*6, 5: [59.5]*12},
    (2001, 2400): {3: [48.5,49,49.5,50.5,51,52,53,54,54.5,55.5,56,57], 4: [57.5,57.5,57.5,58,58,58,58.5,58.5,58.5,59,59,59], 5: [59.5]*12},
    (2401, 3200): {3: [48,48.5,49,50,50.5,51.5,52.5,53.5,54,55,55.5,56], 4: [57.5,57.5,57.5,58,58,58,58.5,58.5,58.5,59,59,59], 5: [59.5]*12},
}

NORTHERN_ALLOWANCES = {
    (0, 1200): {2: [0,0,0,0,0,3,3,3,3,3,3,3], 3: [2.5,2.5,2,2,2,2,1.5,1.5,1.5,1,1,1], 4: [.5,.5,.5,.5,0,0,0,0,0,0,0,0]},
    (1201, 1600): {2: [0,0,0,0,0,3.5,3.5,3.5,3.5,3.5,3.5,3.5], 3: [3,3,2.5,2.5,2.5,2.5,2,2,2,1.5,1.5,1.5], 4: [1,1,1,1,.5,.5,.5,.5,0,0,0,0]},
    (1601, 2000): {2: [0,0,0,0,0,4,4,4,4,4,4,4], 3: [3,3,2.5,2.5,2.5,2.5,2.5,2,2,2,2,2], 4: [1.5,1.5,1.5,1,1,1,.5,.5,.5,0,0,0]},
    (2001, 2400): {3: [3.5,3.5,3,3,3,3,2.5,2.5,2.5,2,2,2], 4: [2,1.5,1,1,.5,0,0,0,0,0,0,0]},
    (2401, 3000): {3: [4,4,3.5,3.5,3.5,3.5,3.5,3.5,3,3,3,3], 4: [2.5,1.5,1,1,.5,0,0,0,0,0,0,0]},
    (3001, 99999): {3: [0,0,0,0,4,4,4,4,4,4,4,4], 4: [3,2,1.5,1.5,1,.5,.5,0,0,0,0,0]},
}


def northern_hemisphere_allowance(race_date: str | date, distance_metres: int,
                                  racing_age: int) -> float:
    """AR170 allowance; caller must first prove northern sire and Jan-Jul foaling."""
    raced = date.fromisoformat(race_date) if isinstance(race_date, str) else race_date
    band = next((bounds for bounds in NORTHERN_ALLOWANCES if bounds[0] <= distance_metres <= bounds[1]), None)
    if band is None:
        return 0.0
    row = NORTHERN_ALLOWANCES[band].get(int(racing_age))
    return float(row[MONTH_INDEX[raced.month]]) if row else 0.0


def standard_weight(race_date: str | date, distance_metres: int, racing_age: int,
                    sex: str | None = None, *, northern_sired_jan_jul_foal: bool = False) -> float | None:
    """Return AR168 standard weight and AR169's 2kg female allowance."""
    raced = date.fromisoformat(race_date) if isinstance(race_date, str) else race_date
    band = next((bounds for bounds in SCHEDULE if bounds[0] <= distance_metres <= bounds[1]), None)
    if band is None:
        return None
    age_key = min(int(racing_age), 5)
    row = SCHEDULE[band].get(age_key)
    if row is None:
        return None
    weight = row[MONTH_INDEX[raced.month]]
    if weight is not None and normalise_sex(sex) in FEMALE_SEXES:
        weight -= 2.0
    if weight is not None and northern_sired_jan_jul_foal:
        weight -= northern_hemisphere_allowance(raced, distance_metres, racing_age)
    return weight


def carried_vs_wfa(carried_kg: float | None, **kwargs: object) -> float | None:
    reference = standard_weight(**kwargs)
    return None if carried_kg is None or reference is None else float(carried_kg) - reference
