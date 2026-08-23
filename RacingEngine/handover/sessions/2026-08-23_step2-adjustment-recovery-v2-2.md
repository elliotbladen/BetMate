# Handover — Step 2 adjustment recovery V2.2

The seven recovery tasks are complete. Step 3 remains blocked.

Implemented `racing_engine/sectional_adjustment.py` and `sectional_adjustment_evaluation.py`. They create meeting/condition corrections, separate three signals, fit from zero by jurisdiction, and evaluate component ablations chronologically. No accepted rating table was changed.

No component passed all gates. Trip compensation is the only sectional signal with consistent next-start MAE improvement, but it worsens NSW race ranking. The achievement blend is zero in both jurisdictions. Steward evidence is useful in Victoria but NSW coverage is missing.

Research supports changing the representation in the next Step 2 experiment: model the complete velocity/energy curve by distance, surface and race phase; include drafting/exposure and late deceleration; do not simply reward a fast final split. See `reports/v2_ratings/sectional_adjustment_v2_2_findings.md` for figures and the frozen V2.3 brief.
