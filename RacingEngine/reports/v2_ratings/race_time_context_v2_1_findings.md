# Race Time Context V2.1 findings

Date: 28 August 2026  
Version: `race-time-context-v2.1-shadow`  
Decision: **not promoted; fitted rating coefficient is zero**

## Build

The ledger uses only clocks available before each race to form track/distance/
going pars, with a track/distance fallback. Rail residuals require ten prior
matching observations. The meeting variant is the median residual of at least
three other races and excludes the race being rated.

Racing.com remains the NSW identity/result owner. Racing NSW rows are used only
as subordinate official-clock observations with explicit provenance. This adds
557 usable NSW observations without reintroducing PDF-derived identities.

- Source clocks available: 2,264
- Point-in-time time figures built: 1,266
- Going-specific pars: 624
- Track/distance fallback pars: 642
- Rail adjustment applied: 105
- Insufficient prior par: 998

## Validation

The coefficient grid was fitted on 2,603 pre-2025 next-start pairs. It selected
**0.0**. Every positive coefficient increased training MAE. Consequently the
candidate cannot improve the 2025 onward NSW or Victorian next-start tests and
fails promotion. A point-in-time horse-state ranking test would also remain
mandatory if a non-zero time candidate were later found.

## Natural Fling

The 15 August Caulfield race used 28 strictly prior Soft 1100 m clocks:

- prior Soft par: 64.97 seconds;
- prior MAD: 0.45 seconds;
- leave-one-race-out meeting variant: −1.375 seconds (meeting faster);
- Natural Fling: 63.91 seconds;
- adjusted residual: +0.315 seconds slow;
- signal: **−0.70 fast MAD**.

Rail was True, but only seven matching prior rail observations existed, below
the fixed minimum of ten; no rail effect was invented.

## WFA/set-weight audit

Natural Fling's official WFA reference was 49.5 kg and she carried 56 kg.
However, 56 kg was the prescribed base carried by almost the entire field in
this three-year-old fillies set-weights-plus-penalties race. Treating the 6.5 kg
absolute difference as individual merit would double-count the race conditions.
Only penalties relative to the prescribed field base may be tested separately.

## Consequence

This family does not close the Natural Fling gap and must remain an evidence
ledger only. Step 1 remains active. The next legitimate candidate is opposition
strength/point-in-time collateral reliability; stewards and trip evidence stay
separate and shadow-only until their jurisdiction and next-start gates pass.
