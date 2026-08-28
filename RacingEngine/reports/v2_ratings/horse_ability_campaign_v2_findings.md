# Horse Ability campaign/layoff findings

## Outcome

Four predeclared campaign treatments were selected on 979 training races. The
no-decay state won:

| Treatment | Training log loss |
|---|---:|
| No decay | 2.34058 |
| Slow decay | 2.34152 |
| Medium decay | 2.34198 |
| Fast decay | 2.34252 |

There is no evidence here for mechanically lowering demonstrated ability just
because a horse has been away. The model therefore retains ability and should
represent layoff through greater uncertainty and current-condition scenarios.

The current scorer does not use uncertainty in its race probabilities. This
experiment consequently tests rating decay, not whether layoff uncertainty is
valuable. An uncertainty-aware evaluator is required before that component can
be judged.

## Named audit and decision

Using chronological initial figures, Sheza Alibi is 110.83 and Gringotts
110.28. Natural Fling is 99.67 from a 104.22 achieved run. Validation improves
on V1 by 0.00464 log loss, but its paired interval includes zero. Keep
shadow-only and proceed to distance/going suitability.
