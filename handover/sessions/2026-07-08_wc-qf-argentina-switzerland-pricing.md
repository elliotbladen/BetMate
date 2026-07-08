# 2026-07-08 — World Cup QFs priced: Argentina vs Switzerland + France vs Morocco (handicaps)

## What was done
Priced the WC2026 quarterfinal Argentina vs Switzerland (Sat Jul 11, Kansas City/Arrowhead, 8pm local) using the WorldCupEngine house template (copied methodology from `price_qf_norway_england.py`).

- New script: `BettingEngine/WorldCupEngine/scripts/price_qf_argentina_switzerland.py`
- Output: `BettingEngine/WorldCupEngine/outputs/qf_argentina_switzerland_pricing.md`

## Inputs (web-confirmed 2026-07-08)
- Argentina path: beat Cape Verde 3-2 AET (R32, Borges OG 111') → beat Egypt 3-2 (R16, from 2-0 down, Messi 8th tournament goal). ELO 2078 → 2087.
- Switzerland path: beat Algeria 2-0 (R32) → 0-0 Colombia, won 4-3 pens (R16, first QF since 1954). ELO 1875 → 1887 (shootout = ELO draw 0.5).
- ELO convention decision this session: AET win = 1.0, shootout = 0.5. Opponents at post-group baseline (matches Norway/England script — not chained through their own knockouts).
- T5: Argentina fully fit (Medina = cramps only). Switzerland banged up: Manzambi (knee) out, Embolo doubt, Widmer hip, Aebischer/Sow/Vargas knocks → atk_b=-0.04, def_b=+0.02.
- Yellow accumulation resets at QF — no suspensions either side.

## Headline numbers
- 90 min: Argentina 55.2% @ 1.81 | Draw 26.8% @ 3.73 | Switzerland 18.0% @ 5.56
- O/U 2.5: Over 48.1% @ 2.08 | Under 51.9% @ 1.93 (xG total 2.6)
- Advance: Argentina 70.1% @ 1.43 | Switzerland 29.9% @ 3.34 (pens split 55.4/44.6)
- Top scorelines: 1-1 (12.8%), 1-0 (11.2%), 2-0 (10.9%)

## Tier coverage (mandatory report)
- T1 ELO: REAL (chained from confirmed results)
- T2 tactical: REAL (both HIGH_PRESS → 1.04/1.04)
- T5 absences: REAL, web-sourced today — but Embolo/Manzambi QF status unconfirmed; re-run at squad news (atk_b=-0.02 if both fit, -0.05 if both out)
- T7 motivation: judgment values (SUI +0.02 historic QF, ARG +0.01)
- T9 pressure: REAL constant (QF = 0.004)
- Recovery tier: neutral by house design — Switzerland played 120min+pens Jul 7 vs Argentina's 90; Swiss price is the optimistic end
- Venue: Kansas City NOT in VENUE_CONTEXT dict — checked manually, ~270m, no altitude adj. Consider adding to `knockout_context.py`.

---

# Game 2 — France vs Morocco (Thu Jul 9, Boston/Gillette) — HANDICAP REQUEST

User asked specifically for Morocco +1 and +2 ("juicy odds" hunch).

- New script: `BettingEngine/WorldCupEngine/scripts/price_qf_france_morocco.py` (adds Asian-handicap pricing off the DC score matrix — reusable pattern for future games)
- Output: `BettingEngine/WorldCupEngine/outputs/qf_france_morocco_pricing.md`

## Inputs (web-confirmed 2026-07-08)
- France: beat Sweden 3-0 (R32) → beat Paraguay 1-0 (R16). ELO 2023 → 2039. Tchouaméni OUT (DM anchor — biggest structural loss, +0.03 opp-facing), Thuram OUT (rotation, -0.01).
- Morocco: 1-1 NED won 3-2 pens (R32) → beat Canada 3-0 (R16). ELO 1828 → 1853. Saibari hamstring doubt (-0.02), Riad CB doubt (+0.02). Motivation +0.02 (2022 SF revenge, Boston diaspora crowd).
- Market at pricing: France -180 / Draw +290 / Morocco +550.

## Headline numbers
- 90 min: France 52.3% @ 1.91 | Draw 27.5% @ 3.64 | Morocco 20.3% @ 4.94
- **Morocco +1.0: fair 1.61** (win 47.7 / push 23.2 / lose 29.1)
- **Morocco +2.0: fair 1.18** (win 70.9 / push 16.5 / lose 12.6)
- Morocco +1.5 fair 1.41 | +2.5 fair 1.14
- Advance: France 67.4% @ 1.48 | Morocco 32.6% @ 3.07
- Model is ~9pts more Morocco-friendly than devigged market on the 90-min ML (model FRA 52% vs market fair ~61%) — the whole "juice" rests on that disagreement. Flagged to user that the WC engine is a light ELO/DC model and unvalidated vs closing lines; no CLV history for this engine.

## First-half addition (user follow-up)
- Added `FIRST_HALF_GOAL_SHARE = 0.45` constant + `build_matrix()` refactor + 1H section to the same script (HT result, 1H AH, 1H totals). Constant is judgment (empirical range 44-46%) — flag for review if 1H pricing becomes a regular thing.
- 1H result: France 37.9% @ 2.64 | HT draw 44.2% @ 2.26 | Morocco 17.9% @ 5.58
- 1H Morocco +0.5 fair 1.61 | +1.0 fair 1.20 (push 25.6%) | +1.5 fair 1.14 | +2.0 fair 1.03 (dead market)
- 1H totals: 0-0 at HT 32.2% @ 3.11 | Over 0.5 @ 1.47 | Under 1.5 @ 1.52

## Follow-ups
- Re-run script when Switzerland matchday squad drops (Embolo/Manzambi).
- Kansas City Stadium missing from VENUE_CONTEXT — add if more games get priced there.
- Repo bracket.py had estimated R32 pairings that diverged from reality (Argentina played Cape Verde/Egypt, not Uruguay/Iran) — bracket.py not updated this session, prices don't depend on it.
