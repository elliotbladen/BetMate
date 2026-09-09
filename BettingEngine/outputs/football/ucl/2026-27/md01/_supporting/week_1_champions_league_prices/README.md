# Week 1 Champions League prices

The UCL player shadow has now been trained, evaluated and run. Nine 90-minute 1X2 research comparisons are saved.

**The six remaining matchday-1 fixtures (Sydney 11 September) are priced in [`md1_remaining_normal_and_shadow/`](md1_remaining_normal_and_shadow/)** — 1X2 and O/U 2.5, normal and shadow, three of six priced normally and one of six in shadow mode. That folder holds the board, the frozen `predictions.csv`, every input and both runs, plus `run/settle.py` to score it once the matches are played.

- [Normal versus player-shadow price board](player_shadow_final/report.md)
- [Prices CSV](player_shadow_final/prices.csv)
- [Full player, tier, source and calculation audit](player_shadow_final/prices.json)
- [Frozen model and input snapshots](player_shadow_final/inputs/)
- [Execution log](player_shadow_execution.log)

The model uses the EPL/EFL Ridge/56-feature/eight-prior-row architecture and +/-0.12 additive goal cap, with UCL-trained coefficients. Minutes were audited using player IDs, substitutions, dismissals and 90/120-minute duration. Predicted lineups use UEFA team news and the sourced Carlos Augusto replacement for Dimarco.

Training: 93 eligible 2024/25 matches. Holdout: 126 eligible 2025/26 matches. Goal MAE improved from 1.168107 to 1.162342; 1X2 RPS improved from 0.198773 to 0.194995. This remains research-only, with no production promotion or bets.

T1 strength, T2 player features plus baseline positional injuries, and T3 domestic form/rest enter the comparison; T0 validates and blocks incomplete inputs. T4 is neutral for MD1, T5 is inapplicable, and T6–T8 are not numerical adjustments. Totals remain withheld.

AEK–LASK, Lille–Betis and Stuttgart–Viking lack comparable baseline strength. Viking's projected Haugen identity remains ambiguous. These three fixtures have no shadow price.

Of 198 projected players in the nine priced fixtures, 22 have fewer than eight valid prior roster records. Coverage counts are retained per player. Slovan uses European history because the attempted ESPN domestic endpoint is unavailable. Expected minutes are estimates, and projected lineups are not confirmed XIs.

The earlier researched_* files, player_shadow_status.json, tier_audit.json, collection_progress files and player_shadow_run1 folder are historical steps; player_shadow_final is the completed run.

Repeat into a new directory:

```bash
.venv/bin/python -m ml.football.ucl_player_shadow --price-output outputs/football/ucl/week_1_champions_league_prices/NEW_RUN
```

To reproduce the frozen inputs explicitly, use scripts/price_ucl_week1_player_shadow.py with --model, --snapshot, --baseline and --history pointing to the corresponding files in player_shadow_final/inputs, plus a new --output directory.
