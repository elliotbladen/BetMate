# NFL Step 8F — T5 rest and scheduling audit

## Decision

Reject T5 as a separate adjustment tier. Retain only the regularised linear rest
difference and rest sum already present in T1. No manual bye, short-week,
Thursday, Monday or rest-mismatch points are authorised.

The audit added nonlinear indicators for short rest (six days or fewer), very
short rest (four days or fewer), long rest (ten days or more), asymmetric rest
advantages, both teams on short/long rest and unusual weekdays. It used 1,599
expanding-window test games from 2019–2024 and within-season shuffled controls.
The 2025 vault was not used.

## Results

| Target | T1 MAE | T1 + T5 MAE | Change | Better seasons |
|---|---:|---:|---:|---:|
| Margin | 10.309 | 10.343 | 0.034 worse | 1/6 |
| Total | 10.767 | 10.785 | 0.019 worse | 2/6 |

T5 also moved farther from the closing spread (2.844 to 2.876 MAE) and closing
total (2.686 to 2.756). The real schedule features performed worse than the
shuffled controls, which is strong evidence that the added complexity is noise
or unstable interaction rather than repeatable signal.

## Operating rule

- Keep T1's learned `rest_diff` for margin and `rest_sum` for totals.
- Do not add a generic post-bye advantage.
- Do not add fixed short-week penalties.
- Do not treat prime-time scheduling as a football edge.
- Travel remains outside this test because distance and body-clock data are not
  available in the historical feature store.
- T5 is disabled, not shadow-promoted.
