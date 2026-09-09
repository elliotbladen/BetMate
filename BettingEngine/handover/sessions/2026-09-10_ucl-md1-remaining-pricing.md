# UCL matchday 1 — pricing the six remaining fixtures — 2026-09-10

User asked for the remaining Champions League games for tomorrow (Sydney 11 September),
1X2 and O/U 2.5, in both normal and shadow mode, saved under week 1.

## Scope

Matchday 1 is eighteen fixtures. Twelve were priced on 8-9 September. The six left are
the European Thursday slate: Fenerbahçe–Roma, PSV–Shakhtar, Bayern–Bodø/Glimt,
Como–Leipzig, Manchester United–Sabah and Slavia Prague–Lens.

## Outcome

Normal mode priced 3 of 6; shadow mode priced 1 of 6.

| Fixture | Normal 1X2 | Normal O/U 2.5 | Shadow |
|---|---|---|---|
| PSV v Shakhtar | 1.97 / 4.36 / 3.81 | O 1.33, U 4.05 | blocked |
| Bayern v Bodø/Glimt | 1.28 / 7.90 / 10.77 | O 1.17, U 6.91 | 1.32 / 7.33 / 9.60, O 1.18 |
| Slavia Prague v Lens | 1.82 / 3.78 / 5.41 | O 2.96, U 1.51 | blocked |

Fenerbahçe, Como and Sabah have no Champions League archive history, so those three
fixtures are blocked on T1 — the same gate that blocked AEK–LASK, Lille–Betis and
Stuttgart–Viking on 9 September.

Shadow blocks are a player-feed limitation, not a model failure. No player feed
available here covers the Czech or Ukrainian leagues, so Shakhtar's ESPN history stops
in January 2025 and Slavia's in January 2026. Three Shakhtar and five Slavia projected
starters have no prior roster record at all, and two more Shakhtar names could not be
resolved against the current squad.

## Built

- `ml/football/ucl_price_league_phase.py` — new league-phase runner. Blocks on club
  identity *before* requiring form/availability context, so a debutant club does not
  need a fabricated domestic feed to be reported as unpriceable; publishes O/U 2.5 from
  the same score matrix as the 1X2 price; and adds a per-fixture `data_health` block.
- `scripts/price_ucl_week1_player_shadow.py` — carries O/U 2.5 through the shadow using
  the same Poisson odds-ratio construction as the EPL/EFL shadow. 1X2 output unchanged.
- `outputs/football/ucl/2026-27/md01/_supporting/2026-09-10_remaining/` — context
  builder, snapshot builder, board builder, archived raw sources, both runs.
- `outputs/.../week_1_champions_league_prices/md1_remaining_normal_and_shadow/` — the
  board, CSV and README, linked from the week 1 README.

## Data findings worth keeping

- **Presence in the archive is not coverage.** Lens are in the ratings on six matches,
  the most recent from September 2023; Slavia on fourteen, Bodø/Glimt on twelve;
  Shakhtar's most recent archive match is 596 days old. The engine still returns a
  confident single number — Lens are given an expected 0.50 goals away at Slavia and
  Bayern an expected 4.07 at home. The new `data_health` block prints the warning next
  to the price. A minimum-history gate is the obvious follow-up.
- **ESPN's `lastFiveGames` is not reliable as a form source.** For Shakhtar it returned
  five Conference League matches from March-May 2026 and no 2026-27 league games at all;
  the club had in fact played five Ukrainian Premier League matches by 5 September. Its
  `gameResult` letters also disagree with the scorelines in the same record.
- **TheSportsDB's free tier truncates silently.** `eventsround` returns five events per
  round in a sixteen-team league, so Slavia's round-6 Prague derby was simply absent
  from an otherwise complete-looking response. Czech and Ukrainian results were taken
  from the Wikipedia season articles instead and reconciled against those articles' own
  league tables (wins, draws, losses, goals for, goals against) before use; both
  reconciled exactly.
- **The raw matrix O/U 2.5 is 4.58 percentage points too high on Over** across 378
  held-out matches (Brier 0.24398, mean Over 70.45% vs actual 65.87%). The archived
  isotonic calibration lowers Brier to 0.22964 but flattens discrimination — it prices
  these three very different fixtures at 1.61, 1.81 and 1.83 on Over. Both are published
  so the gap is visible; neither is a betting price.

## Not done / limits

- uefa.com was unreachable (HTTP/2 INTERNAL_ERROR and timeouts), so availability comes
  from the archived 7 September team-news page and is three days stale.
- No matchday-1 referee appointments were published in any source consulted; T6 unpopulated.
- The strength fit runs to 30 May 2026 and excludes Wednesday's twelve matchday-1 results.
- Absences use ESPN squad position groups mapped to the generic role in each group, so an
  absent full-back is priced with centre-back weights.
- No market quotes, no EV, no bets. ESPN's odds block was inspected and rejected: the
  Bayern–Bodø/Glimt record carried a `details` string of "MUN -1100".

## Tests

`.venv/bin/python -m pytest tests -q` → 255 passed, 3 failed. All three failures are
pre-existing and unrelated: two need `pyarrow`/`fastparquet`, which are not installed,
and `test_detect_afl_round_uses_latest_prepared_round` asserts an AFL round number that
local data no longer matches. The 61 football/UCL/player tests all pass.

Backward compatibility of the shadow-pricer change was checked by re-running the
8 September job with its own defaults: `prices.csv` and the report price table come back
byte-identical, because the totals block only appears when the baseline supplies totals
and the 8 September baseline does not.
