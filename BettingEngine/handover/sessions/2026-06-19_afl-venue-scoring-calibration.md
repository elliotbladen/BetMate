# Handover — AFL Venue Scoring Calibration (2026-06-19)

## What was done

Replaced the AFL T4B venue scoring profile with real season-adjusted data computed
from the historical odds xlsx (3474 games, 2018-2026 regular season).

### Problem with old values

The original `VENUE_SCORING_PROFILE` in `pricing/afl_tier4_venue.py` was built from:
- Raw deviations from a static league average (no season adjustment)
- Then scaled by 30% ("ML captures 70% via venue_avg_total feature")

This approach was wrong in two ways:
1. No season adjustment → scores like 2018 (low) confused with 2022+ (higher), inflating
   or deflating individual venue readings based on which years they hosted games
2. The 30% scaling was an arbitrary guess, not calibrated against anything

Two venues were in the WRONG DIRECTION as a result:
- **The Gabba: -1.0 → +2.4** (Brisbane Lions are an offensive team, not defensive)
- **People First Stadium: -4.6 → +2.0** (Gold Coast is an open-air attacking ground)

### Method used

Script: `scripts/_build_afl_venue_profiles.py`

1. Load xlsx (header=1), filter regular season (Playoff=0/NaN), 2018+
2. Compute season average per year (removes year-to-year drift)
3. Residual per game = actual_total − season_avg[year]
4. Venue delta = mean(residuals)
5. Blend: 70% recent-3yr + 30% all-time (fall back to all-time if n_recent < 8)
6. Clamp at ±10 pts

Venue name normalisation in the script handles historical renames:
- Docklands / Etihad → Marvel Stadium
- Blundstone Arena → UTAS Stadium
- Kardinia Park → GMHBA Stadium
- GIANTS Stadium / Spotless / Sydney Showground → ENGIE Stadium
- Heritage Bank / Metricon / Cbus → People First Stadium

### Results (blended, season-adjusted)

| Venue | Old | New | Δ | Notes |
|-------|-----|-----|---|-------|
| UTAS Stadium | −1.5 | **−10.0** | −8.5 | Was 7× too small |
| Blundstone Arena | −1.5 | −10.0 | − | alias |
| Optus Stadium | −0.9 | **−7.8** | −6.9 | Perth — dry + defensive |
| Adelaide Oval | −0.9 | **−4.2** | −3.3 | Wind off Torrens river |
| MCG | 0.0 | **−3.9** | −3.9 | Large open stadium |
| Manuka Oval | +1.2 | **+0.7** | −0.5 | Small recent sample |
| People First Stadium | −4.6 | **+2.0** | +6.6 | ⚠️ Direction FLIP |
| Ninja Stadium | +1.5 | +2.3 | +0.8 | Small recent sample |
| The Gabba | −1.0 | **+2.4** | +3.4 | ⚠️ Direction FLIP |
| Gabba | −1.0 | +2.4 | − | alias |
| Marvel Stadium | +1.9 | **+4.5** | +2.6 | Enclosed, counter-intuitively high |
| Docklands/Marvel | +1.9 | +4.5 | − | alias |
| SCG | +0.5 | **+5.4** | +4.9 | Compact fast surface |
| GMHBA Stadium | +1.5 | **+6.0** | +4.5 | Geelong home — strong over |
| Kardinia Park | +1.5 | +6.0 | − | alias |
| ENGIE Stadium | +2.0 | **+8.7** | +6.7 | GWS home — highest scorer |
| TIO Stadium | −3.0 | **+10.0** | +13.0 | Darwin heat → frenetic play |
| Cazalys Stadium | −3.0 | −3.0 | 0 | No data, kept conservative |
| Traeger Park | −3.0 | −3.0 | 0 | No data, kept conservative |

T4_TOTALS_CAP raised from 5.0 → **10.0** (allows ENGIE +8.7 and UTAS −10.0 through).

### Files changed

- `pricing/afl_tier4_venue.py` — VENUE_SCORING_PROFILE replaced, T4_TOTALS_CAP 5.0→10.0
- `scripts/_build_afl_venue_profiles.py` — NEW — reproducible computation script

### Impact on AFL R15

Re-ran `prepare_afl_round.py --season 2026 --round 15` and `_export_afl_prices.py --round 15`.

| Game | Venue | Old t4_tot | New t4_tot | Total old | Total new |
|------|-------|-----------|-----------|-----------|-----------|
| Dockers vs Cats | Optus | −0.9 | −7.8 | 197.4 | 187.0 |
| Suns vs Hawks | People First | −4.6 | +2.0 | 168.5 | 175.1 |
| Crows vs Demons | Adelaide Oval | 0.0 | −4.2 | 183.1 | 178.9 |
| Magpies vs Power | MCG | 0.0 | −3.9 | 166.4 | 162.5 |
| Giants vs Blues | ENGIE | +2.0 | +8.7 | 177.1 | 183.8 |
| Tigers vs Roos | MCG | 0.0 | −3.9 | 156.5 | 152.6 |
| Saints vs Dogs | Marvel | +1.9 | +4.5 | 174.2 | 176.8 |

## Context note on confounded venues

UTAS (Hawthorn), People First (Gold Coast), ENGIE (GWS) are single-team venues.
Their venue delta is partially confounded with their home team's playing style.
This is acceptable for prediction: if Hawks play at UTAS, the historical
Hawthorn-at-UTAS totals are the correct reference regardless of causation.

The Gabba direction flip is the most striking: the old guess (-1.0) was likely
based on an era when Brisbane was defensive. The 2021-2026 Lions era is attacking
and produces above-average scores.

## Session also covered (in prior context)

The prior session context included:
- NRL R16 pricing with T6 home bias calibration (Klein +3.20, Sutton −3.14)
- `scripts/_ref_home_bias.py` — built referee home margin analysis from DB
- `scripts/_ref_bias_totals_research.py` — confirmed NO independent totals effect
- `pricing/tier6_referee.py` — wired `home_bias_adj` field into handicap
- `config/tiers.yaml` + `config/sports/nrl.yaml` — raised handicap_clamp 1.5→3.5
- AFL umpire research — concluded not worth building (41 umpires, 3-4 per game, diluted signal)

## Pending

- AFL R15 has large rules/ML divergences on most games — BETTING RULE: only bet where
  both models agree direction. R15 has many disagreements (Giants vs Blues is
  biggest: rules +29.7 vs ML −3.1). Approach with caution.
- Re-run AFL from R12 backward to back-test whether new venue values improve model
  accuracy vs market (optional but informative)
- G3 Origin squad populate before R18 (camp starts July 3)
- Supabase UNIQUE constraint on `betmate_data_store.key` column
- AFL sigmoid ELO scaling (end-of-season)
