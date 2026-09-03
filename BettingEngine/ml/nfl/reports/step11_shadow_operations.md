# NFL Step 11 — weekly prospective shadow operations

The research build is operated as a frozen weekly shadow. Each checkpoint
re-reads readiness gates, writes a timestamped report and keeps T1 separate from
unresolved T2/T3, T6, T8 and T9 inputs.

The runner cannot place a bet, enable staking or retune thresholds. Missing
quotes, injuries, QB confirmations, continuity or weather coordinates produce a
blocked checkpoint and `ABSTAIN` for every game.

Run from `BettingEngine` with:

```text
python -m ml.nfl.step11_shadow_run
```

After live inputs become available, the same frozen T8/T9 rules are evaluated
after the market opens. Promotion remains gated at 500 frozen predictions, two
seasons and 90% market coverage with audited lines and positive CLV.
