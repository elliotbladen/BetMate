# 2026-07-10 — Soccer tabs scaffolding (EPL / Championship / UCL)

## What was asked
Three new odds-board tabs alongside NRL/AFL: EPL, Championship, Champions League. Architecture + plumbing only — hook-up happens next week once the Odds API renews (~Tue Jul 14).

## What was built (build passing ✅, tsc clean, no runtime data expected yet)

| Piece | File | Notes |
|-------|------|-------|
| Sports config (SoT) | `lib/sports.ts` (new) | All 5 sports: ids, tab labels, Odds API keys (`soccer_epl`, `soccer_efl_champ`, `soccer_uefa_champs_league`), endpoints, per-sport feature flags. Soccer = everything off (pure odds board). `enabledSports()`, `isSoccer()`, `isSportId()` helpers |
| Odds API route | `app/api/odds/[league]/route.ts` (new) | Dynamic allowlist route for the 3 soccer leagues; snapshot fallback; static nrl/afl routes take precedence. `/api/odds` prefix already public in middleware — verified, no change needed |
| Team badges | `lib/soccerTeams.ts` (new) | EPL 20 / Championship 26 / UCL 28 clubs with abbr + colours. Wired into `getTeamMeta()` in `lib/teams.ts`. ⚠️ Names seeded blind (feed down) — verify vs first live response |
| Snapshot fallback | `lib/oddsSnapshotFallback.ts` | SnapshotSport extended to the 5 sports |
| Odds page | `app/odds/page.tsx` | `Sport` type now from lib/sports; tabs from `enabledSports()`; one shared `soccerGames` state + fetch effect (60s poll, same as footy); refs/venues/weather/team-news/predictions/completed/movements all sport-gated to NRL/AFL; `?sport=` param validated via `isSportId` |
| Header tabs | `components/layout/Header.tsx` | Mobile/desktop sport pills now from config (5 tabs). File has pre-existing mojibake in comments — only ASCII lines touched |
| Affiliate links | `lib/affiliate.ts` | `buildGameUrl` accepts soccer sports: Neds/Ladbrokes get search URLs, rest get soccer landing pages (`SOCCER_URLS`). `getAffiliateUrl` soccer-aware |
| Snapshot scraper | `scrapers/odds_snapshot.py` | 3 soccer keys added — collection auto-starts when the key renews. Monday baseline push deliberately stays NRL/AFL |

## Design decisions
- **Feature flags over conditionals:** every sport-specific feature reads (or will read) `SPORTS[id].features`. Soccer starts as a bare odds board; each feature lights up by flipping a flag + wiring its data source. No fake/empty panels.
- **Graceful degradation everywhere:** unknown team -> plain-text badge; no venue -> weather skipped; no predictions endpoint -> no model line. Nothing crashes on missing soccer data.
- **NRL/AFL untouched behaviourally** — their fetch effects, movements, and fallbacks are unchanged; soccer is additive.

## Hook-up checklist (next week, in rough order)
1. Odds API renews -> run a snapshot cycle -> confirm `/api/odds/epl` etc. return events (off-season: EPL/Championship empty until August, UCL until September — expected).
2. **Verify team names** in `lib/soccerTeams.ts` against the live feed (Bournemouth/Brighton/Wolves naming variants + 2026-27 promotions/relegations).
3. **Draw column**: soccer H2H is 3-way; `extractH2HOdds()` drops the Draw outcome today. Needs an extractor variant + a third column on soccer H2H cells.
4. Totals: soccer lines are goals (2.5) — check display copy that says points.
5. Predictions: BettingEngine `ml/football` (EPL done, Championship Phase 2) -> push script -> `/api/epl-predictions`-style routes -> **middleware PUBLIC_PATHS in the same commit** -> flip `features.predictions`.
6. Soccer opening baselines in `push_opening_baseline()` if movement arrows are wanted (EPL rounds are weekend-based; "Monday baseline" logic needs a think).
7. Verify bookmaker soccer landing URLs in `lib/affiliate.ts` (guessed, not tested).
8. Odds API budget: 3 extra sports x 2 snapshots/day is a few hundred calls/month vs ~30k budget — fine, but recheck once reactive snapshots exist for soccer.

## Session context
Same machine/day as the NRL R19 + Championship engine Phase 1 sessions. Odds API + betmate.au intentionally down until ~Jul 14 — nothing in this scaffolding was runtime-tested against live odds; build + typecheck are the verification. Deploying is safe (tabs render with empty states consistent with the site's current paused state).
