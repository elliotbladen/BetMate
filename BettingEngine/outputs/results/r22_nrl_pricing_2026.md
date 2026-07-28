# NRL Round 22 2026 — Full Pricing (2026-07-28)

Games: Thu 30 Jul – Sun 2 Aug 2026. Priced fresh this session after backfilling a
skipped Round 21 (fixture + results were never loaded — inserted manually from
NRL.com draw data before this round's ELO could be trusted).

## Tier coverage — mandatory report

| Tier | Status | Notes |
|------|--------|-------|
| T1 Baseline (ELO) | ✅ Real | Rebuilt through R21 results (backfilled this session) |
| T2 Style matchup | ✅ Real | Fresh Fox Sports style-stats scrape (R22) |
| T3 Momentum/situational | ✅ Real | Rest/travel computed from fixture + DB |
| T4 Venue | ✅ Real | All 8 venues resolved (Glen Willow required an alias fix) |
| T5 Injuries | ✅ Real | Fresh Zero Tackle scrape, 81 records, 72 loaded (9 didn't match roster — see below) |
| T6 Referees | ⚪ Not available | Refs not yet announced by NRL (normal — posted Wednesdays). T6=0.0 all games |
| T7 Weather | ✅ Real | Tomorrow.io, 8/8 games |
| T9 Matrix confluence | ✅ Real | 3+ way confluence found on all 8 games |
| T10 Origin | ⚪ Correctly dormant | Origin season ended G3 (Jul 8–9); no active camp window |
| Market/EV comparison | ❌ Unavailable | Odds API still returning 401 (subscription lapsed since ~Jul 3, still not renewed as of today) |

**7 of 9 model tiers fully populated with real data this round** (78%) — the two gaps
(T6, T10) are both genuine "nothing to report" states, not scraper failures. Market EV
cannot be computed until the Odds API key is renewed.

## Data-quality note
R21 (Jul 23–26) had never been fetched into the DB — fixture and results were missing
entirely, meaning ELO going into this round would have been one round stale. Backfilled
by pulling the R21 draw from NRL.com and loading both fixture + final scores before
rebuilding this round's baseline.

## Pricing sheet (fair, from `results/r22_pricing_2026.csv`)

| Game | Venue | Fair margin | Fair H2H | Fair total |
|------|-------|------------|----------|------------|
| Cowboys v Roosters | QCB Stadium | Roosters -9.5 | 4.67 / 1.27 | 44.5 |
| Dragons v Dolphins | WIN Stadium | Dolphins -10.3 | 5.12 / 1.24 | 45.9 |
| Storm v Bulldogs | AAMI Park | Storm +4.4 | 1.55 / 2.83 | 36.7 |
| Titans v Warriors | Cbus Super Stadium | Warriors -14.8 | 9.20 / 1.12 | 37.6 |
| Panthers v Raiders | Glen Willow | Panthers +10.9 | 1.22 / 5.50 | 44.7 |
| Broncos v Knights | Suncorp | Broncos +5.9 | 1.46 / 3.18 | 47.6 |
| Sharks v Rabbitohs | Ocean Protect | Sharks +12.1 | 1.19 / 6.38 | 53.3 |
| Tigers v Eels | CommBank | Tigers +0.8 | 1.91 / 2.10 | 49.1 |

## T9 matrix confluence (3+ way, same direction)

- **Tigers v Eels** — 6-way HANDICAP → home covers (Eels long rest ≥10d is the biggest single edge at 62%); 5-way H2H → away win. Conflicting market signals — model alignment check would be needed once market lines return.
- **Sharks v Rabbitohs** — 5-way H2H → home win, 4-way HANDICAP → home covers, 4-way TOTALS → unders. Clean triple stack, same direction.
- **Dragons v Dolphins** — 5-way HANDICAP → away covers (stronger than the competing 3-way home-covers signal) + 3-way H2H → away win. Consistent with the model's own -10.3 Dolphins line.
- **Storm v Bulldogs** — 4-way H2H → home win + 4-way HANDICAP → away covers (conflicting directions between markets — handicap confluence favours Bulldogs covering despite Storm expected to win outright, consistent with model's own tight +4.4 margin).
- **Titans v Warriors** — 4-way H2H → away win vs 3-way → home win (split signal, model itself has Warriors -14.8 clear favourite).
- **Cowboys v Roosters** — 3-way HANDICAP → away covers.
- **Panthers v Raiders** — 3-way HANDICAP → home covers, consistent with model's own +10.9 margin.
- **Broncos v Knights** — 3-way H2H → home win (100% on the "vs Newcastle Knights" row), consistent with model's own +5.9 margin.

## Key T5 injury notes
- **Storm**: Cameron Munster AND Harry Grant both out (elite) — 9.0pt hcap impact, the single biggest injury hit of the round, yet model still has Storm +4.4 on ELO strength alone.
- **Rabbitohs**: Latrell Mitchell out (elite) plus 8 rotation-tier outs — 7.0pt impact, reinforcing the Sharks' handicap/H2H confluence stack above.
- **Knights**: Dylan Brown out (key) plus Kalyn Ponga among 8 total outs — 4.8pt impact.
- 9 of 81 scraped injury records didn't match a current-round roster line (kickoff mismatch/spelling) — flagged as errors during load, did not silently drop into pricing.

## Can't-price / open items
- **Market EV**: impossible until Odds API renews — every game has open EV comparison disabled this week, same as the Jul 3–28 gap.
- **T6 referees**: re-run `nrl_referees.py` Wednesday afternoon once NRL posts appointments, then re-price T6 only (all other tiers are already final).
- **R21 backfill**: was reconstructed from NRL.com only (no odds/injuries/emotional context for that round) — it exists in the DB purely to keep ELO current, not as a priced round. Do not expect a R21 pricing writeup.
