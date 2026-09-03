# NFL Step 12 — prospective promotion ledger

The model is now ready to collect evidence in a single append-only ledger. Each
row identifies the frozen prediction and T9 threshold version, records whether
the true opener and obtainable price were verified, and stores CLV and result
fields when available.

The ledger starts empty. It cannot promote a tier, enable staking or accept a
manual override. Promotion requires 500 frozen predictions, two seasons, 90%
market coverage, audited openers and prices, positive CLV and a positive opening
line beat rate. Threshold version changes invalidate the sample for promotion.

Run the status check from `BettingEngine` with:

```text
python -m ml.nfl.step12_promotion_ledger
```
