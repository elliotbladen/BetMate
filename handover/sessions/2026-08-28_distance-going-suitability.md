# Distance/going suitability handover

Date: 2026-08-28

Implemented `racing_engine/horse_ability_suitability_v2.py` and its unit tests.
The model forms strictly prior, horse-specific residual profiles for sprint,
mile, middle and staying distances and dry, soft and heavy going. It requires
two matching runs, shrinks sparse estimates and caps each dimension at six
points.

Selection across 25 coefficient combinations used 979 training races only.
Zero distance and zero going were selected at 2.34058 training log loss; all
positive combinations were worse. No context adjustment was carried into base
Horse Ability. This preserves Sheza Alibi 110.83 above Gringotts 110.28 on
initial chronological figures and Natural Fling at 99.67.

The component is frozen at zero. Distance/going profiles belong in later
race-specific expected-performance scenarios unless a future independent test
supports them. Next task is the final Horse Ability validation/freeze gate.
