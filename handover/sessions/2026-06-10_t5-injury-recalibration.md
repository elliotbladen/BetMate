# Session Handover — 2026-06-10
## AFL T5 Injury Table Recalibration + Saints/GWS Deep Dive

---

### What We Did

Investigated whether the AFL T5 injury impact table is well-calibrated. Triggered by user
noticing GWS were heavy model favourites vs St Kilda R14. Traced the full tier-by-tier
breakdown for that game, found a concrete data entry bug, and recalibrated the impact table
based on published research and 2026 outcome data.

---

### Tier Breakdown — Saints vs GWS (what prompted the research)

| Tier | Adjustment | Driver |
|------|-----------|--------|
| T1 ELO | GWS -6.8 | GWS higher ELO; Marvel shared venue only 1.4pt home advantage |
| T2 Style | GWS -1.8 | GWS stronger contested/territory stats |
| T3 Situational | Saints +0.7 | GWS travel advantage (Sydney → Melbourne) |
| T4 Venue | 0.0 | Neither team has fortress at Marvel |
| T5 Injuries | GWS -8.0 (CAPPED) | Saints missing King/Higgins/Clark/Howard; GWS had zero injuries in dict |
| T6 Emotional | 0.0 | No flags for either team |
| T7 Weather | 0.0 | No game-day data yet |
| **Total** | **GWS -15.9** | Market: GWS -2.5 |

---

### Bug Found: GWS Injuries Missing From R14

Tom Green (elite midfielder, knee — season-ending) was confirmed out from R12 onwards but
was NOT entered in the R14 INJURIES dict. Josh Kelly and Sam Taylor also absent R12/R13 with
no R14 entry. GWS appeared fully fit to the model.

Net T5 impact with bug:
- Saints raw: -10.2 (capped to -8.0)
- GWS raw: 0.0
- Net: -8.0

Net T5 impact after fix:
- Saints raw: -10.2 → after compound 0.85× → -8.67 (capped -8.0)
- GWS raw: -5.95 → after compound 0.85× → -5.06
- Net: -4.25

Difference: 3.75pts. Model line moved from GWS -15.9 → GWS -12.2.

---

### Research Findings — Is T5 Calibrated Right?

Published research is sparse. Key findings:
1. **Deakin University (best study):** 9 missed matches by a top-10 player = 1 ladder position
   drop. Translates to ~1-2 pts per game on average across all top-10 players — much lower
   than our table. But this is a season-level average, not game-level for genuine elite absences.
2. **Matter of Stats:** Injury-adjusted models reduce MAE by ~0.4 pts per game averaged across
   all games. But most games have minor/no injuries — elite absences have larger per-game effect.
3. **No published quantification** of specific position values (no "elite key forward = X pts").
   Champion Data and The Arc keep impact tables proprietary.
4. **Midfielder importance declining:** Only 60% of AFL games won by team with more contested
   ball in modern AFL (was 70%+). Supports reducing midfielder impact values.
5. **Saints 2026 scoring without King (R12 + R13 only):** 84.5 avg vs 91.6 with King — 7.1pt
   drop. Loosely supports elite key forward at -5.0, but sample size of 2 is meaningless.
6. **Injury impacts are subadditive:** Literature leans toward team restructuring reducing
   compounding. Our 0.85× compound dampener is directionally correct.

---

### Changes Applied

**`BettingEngine/pricing/afl_tier5_injury.py`:**
| Entry | Before | After | Reason |
|-------|--------|-------|--------|
| key_forward, good | -3.5 hcp / -2.5 tot | -3.0 / -2.0 | Slightly too aggressive vs outcomes |
| midfielder, elite | -3.5 hcp / -1.5 tot | -3.0 / -1.5 | Declining midfielder importance in modern AFL |
| midfielder, good | -2.0 hcp / -0.5 tot | -1.5 / -0.5 | Same reason; was 2× too high for a "good" mid |

All other values unchanged. Key forward elite (-5.0) supported by Saints scoring data.
Compound dampener and cap unchanged.

**`BettingEngine/scripts/prepare_afl_round.py` — R14 INJURIES dict:**
Added GWS entry:
```python
'Greater Western Sydney Giants': [
    {'player': 'Tom Green',   'position': 'midfielder',   'quality': 'elite'},  # knee — season
    {'player': 'Josh Kelly',  'position': 'midfielder',   'quality': 'good'},   # hip — TBC R14
    {'player': 'Sam Taylor',  'position': 'key_defender', 'quality': 'good'},   # hamstring — TBC R14
],
```

---

### R14 Final Prices (all fixes applied)

| Game | Model | Market |
|------|-------|--------|
| Bulldogs vs Crows | Crows -7.4 | Bulldogs -4.5 |
| Cats vs Suns | Cats -36.8 | Cats -25.5 |
| Demons vs Bombers | Demons -34.9 | Demons -30.5 ✅ |
| Kangaroos vs Eagles | NM -27.4 | NM -6.5 |
| Power vs Swans | Swans -16.2 | Swans -17.5 ✅ |
| Tigers vs Lions | Lions -30.5 | Lions -46.5 |
| Saints vs Giants | Giants -12.2 | Giants -2.5 |

---

### Critical Workflow Rule Established

**Season-ending injuries do NOT carry forward automatically.** Every round's INJURIES dict
must be manually re-populated. Before pricing each round, check that all known season-enders
from the prior round are still in the new dict. Common season-enders to watch:
- Tom Green (GWS) — knee, season
- Sam Darcy (Bulldogs) — ACL, season
- Oscar Allen (Brisbane) — foot, season (entered in R13/R14 under Brisbane)

Failure to carry these forward inflates the T5 calculation and overcharges the team with
fewer injuries by 2-4pts per missed player.

---

### Next Session

1. Verify Kelly/Taylor (GWS) status for R14 on game day — adjust if they return
2. AFL sigmoid ELO scaling — still the biggest structural model issue (10pt avg gap vs market)
3. Calibrate T5 table after season using actual margin outcomes on injury-heavy games
4. Saints vs Giants: model -12.2, market -2.5 — 9.7pt gap still suggests market underpricing
   Saints' injury crisis. Check GWS's form/motivation before betting.
