# UCL constraints and mitigation plan

| Constraint | Solution | Promotion gate |
|---|---|---|
| Closing prices not always timestamp-confirmed | Store source URL, retrieval time, quote time, bookmaker and market; classify confirmed/proxy; report separately | No mixing proxy and confirmed CLV |
| Missing true UCL xG | Import event feeds; train a competition-aware xG model; retain goals fallback with a source flag | xG coverage and out-of-sample Brier improvement |
| Cross-league strength differences | Fit league effects with partial pooling; combine domestic xG, ClubElo and UEFA prior | Stable ratings across expanding windows |
| UEFA coefficient hindsight | Snapshot coefficients as-of season start and version every file | Reject rows without as-of timestamp |
| Club/date mapping errors | Canonical registry, alias table, fuzzy-match quarantine and one-to-one fixture checks | 100% mapped or explicitly quarantined |
| Small two-season sample | Use multi-season training, but reserve 2024/25–2025/26 as the primary test; bootstrap confidence intervals | No promotion on point estimate alone |
| Format change | Separate legacy group-stage and modern league-phase tracks | Never pool format eras in one metric |
| Historical injuries/line-ups | Use only reports published before kickoff; retain player layer as shadow until coverage is complete | No leakage and independent shadow lift |
| Overconfident probabilities | Isotonic/logistic calibration by market and stage; cap/shrink extreme edges | Calibration error and CLV gates pass |
| Knockout variance | Monte Carlo aggregate state with extra time/penalties and official draw rules | Tie-level validation before betting |

## Operating rule

When an input is missing or ambiguous, the model abstains or falls back to a labelled lower-information state. It never silently imputes a high-confidence feature. Every backtest row carries source, as-of timestamp, format era and confidence flags.
