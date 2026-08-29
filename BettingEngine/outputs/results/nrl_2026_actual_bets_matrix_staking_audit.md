# 2026 NRL actual bets — H2H/handicap matrix staking audit

## Scope

- Source: checked-in BetMate actual-bet ledger.
- Included: 2026 NRL bets with an explicit team and a fixture match.
- Excluded: totals, props, multis, State of Origin and ledger records whose selected side is unclear.
- Matrix source: frozen 2022–2025 NRL H2H and handicap matrices; no 2026 results were added to the matrix.

## Eligible-bet signal counts

| Matrix support rule | Bets | Wins–losses | P&L at actual stake | Increment if doubled |
|---|---:|---:|---:|---:|
| 3+ aligned 10% signals; no opposing 10% signal | 5 | 2–3 | $-47.80 | $-47.80 |
| 3+ aligned 20% signals; no opposing 20% signal | 4 | 2–2 | $-12.50 | $-12.50 |
| 3+ aligned 30% signals; no opposing 30% signal | 0 | 0–0 | $+0.00 | $+0.00 |
| 3+ aligned 40% signals; no opposing 40% signal | 0 | 0–0 | $+0.00 | $+0.00 |

## Predefined double-stake test

Rule: double only where the relevant matrix had **3+ aligned signals at 20%+** and **zero opposing 20%+ signal**. This mirrors the existing T9 confluence convention; it was fixed before calculating the staking result.

- Eligible bets: **57**; excluded/unmatched: **42**.
- Actual eligible-bet P&L: **$+361.29**.
- Qualifying double-stake bets: **4**.
- Counterfactual P&L: **$+348.79**.
- Change from doubling: **$-12.50**.

## Qualifying bets

| Date | Bet | Result | Stake | Support / conflict |
|---|---|---:|---:|---|
| 2026-05-03 | Cronulla -7.5 — Cronulla Sharks vs Wests Tigers | win | $50.00 | 33% vs Wests Tigers, 32% After a Loss, 26% Ocean Protect Stadium, 21% Cover Rate — Home |
| 2026-05-09 | Dragons +8.5 — St George vs Newcastle | loss | $50.00 | 36% WIN Stadium, 29% Cover Rate — Home, 25% Long Rest (≥ 10 days), 22% After a Loss |
| 2026-05-10 | Canberra Win — Canberra vs Penrith | loss | $50.00 | 58% May, 23% vs Penrith Panthers, 23% Sunday Games |
| 2026-05-15 | Dolphins Win — Rabbitohs vs Dolphins | win | $50.00 | 35% May, 34% Thursday / Friday Games, 23% Night Games (kick-off ≥ 18:00) |

## Exclusions

Totals are deliberately out of scope. The remaining exclusions lack an unambiguous selected side in the current ledger, so guessing would make the experiment unreliable.

- selected team not explicit in ledger: **5**
- totals/prop/multi or unsupported market: **37**

## Important limitation

This is a retrospective, small-sample staking experiment—not evidence that the matrix creates a predictive edge. The matrix uses overlapping historical splits, so three signals are not three independent pieces of evidence. Do not deploy doubled stakes from this result alone; test the rule prospectively next season with the rule frozen.
