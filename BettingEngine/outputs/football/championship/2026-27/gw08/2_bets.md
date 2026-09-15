# Championship GW8 — EV screen and bet decision (1X2)

**Entry rule:** ≥10% EV at the best available price · Market: Odds API (uk), ~20 books,
2026-09-15

## Recommendation: **no bets**

Nine outcomes clear 10% EV. None is taken. The reasons are specific.

⚠️ **Market data note:** the raw feed carried several **`1000.0`** quotes — placeholder
prices from books with suspended markets, on Bristol City, Birmingham, Lincoln and QPR.
Taken at face value they produce absurd EVs. All quotes above 40.0 are filtered; every
price below is from a real market with ~20 books.

## The screen

| fixture | model 105% H/D/A | market H/D/A | EV H | EV D | EV A |
|---|---|---|---|---|---|
| Bristol City v Watford | 2.08 / 3.32 / 3.73 | 1.96 / 3.60 / 3.90 | −10.2% | +3.1% | −0.5% |
| **Cardiff v Charlton** 🆕 | 2.82 / 3.07 / 2.70 | 1.75 / 4.20 / 4.50 | −41.0% | **+30.1%** | **+58.9%** |
| **Millwall v West Ham** 🆕 | 2.86 / 3.21 / 2.57 | 4.10 / 4.00 / 1.83 | **+36.6%** | **+18.6%** | −32.2% |
| Stoke v Sheffield United | 2.56 / 3.25 / 2.84 | 2.60 / 3.60 / 2.78 | −3.3% | +5.5% | −6.9% |
| Birmingham v Middlesbrough | 2.93 / 3.58 / 2.33 | 3.00 / 3.60 / 2.40 | −2.3% | −4.2% | −2.0% |
| Portsmouth v Blackburn | 2.57 / 3.25 / 2.83 | 2.18 / 3.50 / 3.70 | −19.1% | +2.5% | **+24.4%** |
| Burnley v Derby 🆕 | 1.87 / 3.67 / 4.13 | 1.85 / 3.75 / 4.30 | −5.7% | −2.6% | −0.8% |
| Lincoln v Swansea 🆕 | 2.38 / 3.31 / 3.05 | 2.75 / 3.50 / 2.50 | +9.9% | +0.8% | −22.0% |
| QPR v Preston | 1.98 / 3.49 / 3.88 | 1.74 / 4.00 / 4.90 | −16.2% | +9.1% | **+20.3%** |
| Wrexham v Southampton | 2.84 / 4.00 / 2.24 | 3.10 / 3.75 / 2.32 | +4.1% | −10.6% | −1.2% |
| Wolves v West Brom 🆕 | 2.06 / 3.33 / 3.77 | 1.80 / 3.80 / 4.80 | −16.9% | +8.6% | **+21.3%** |
| Norwich v Bolton 🆕 | 1.74 / 3.81 / 4.67 | 1.60 / 4.60 / 5.70 | −12.6% | **+15.0%** | **+16.3%** |

🆕 = contains a club new to the division, priced by `elo_seeded`

## Why none of them is a bet

### The two loudest edges both sit on the brand-new code path

**Charlton +58.9%** and **Millwall +36.6%** are the biggest numbers on the card, and both
fixtures contain a club new to the division — Cardiff and West Ham. Those ratings come
from `elo_seeded`, merged **today**, which has never priced a live round before.

Its walk-forward record is genuinely good (better in 10 of 10 seasons). That is still not
the same as live use, and the rule this repo keeps relearning is that **the largest
model-vs-market gap is usually a broken or untested input, not an opportunity.** Taking
the two biggest edges on the card as the debut of a new mode inverts that.

In both cases the model is fighting a strong market opinion: the market has Cardiff at
1.75, the model has the game near even (33.7 / 31.0 / 35.3); the market has West Ham at
1.83, the model has Millwall the slight favourite. A 20-book consensus is not usually
that wrong.

### Four of the nine qualifiers are draws, and draws are systematically mispriced here

Model mean P(Draw) is **27.8%** against a de-vigged market **25.5%** — **+2.3pp**. EPL
GW5 showed the same tilt in the same direction. The engine has **no 1X2 calibrator**, and
an inflated draw is what an uncalibrated Dixon-Coles produces. Every draw EV on this card
inherits that bias, so +30.1%, +18.6%, +15.0% and +9.1% on the draw are the bias showing
up as value.

Over-weighting the draw also *creates* away-side value once the book normalises, which
casts doubt on the away qualifiers at Portsmouth, QPR and Wolves too.

### T5 was audited properly, and it genuinely comes to zero

Originally T5 was skipped on the grounds that published absentees are usually already in
the ratings. That was the right instinct applied the wrong way — skipping a tier handles
the stale-absentee case and misses fresh injuries entirely, and only a filter separates
the two. So the filter was built.

**Method.** ESPN player appearances were backfilled to cover GW7 (69 → 81 fixtures,
3,238 player rows, current to 13 Sep). Every published absentee from
sportsgambler.com/injuries (retrieved 15 Sep, all 24 clubs) was then tested:

1. did they feature in one of their club's **last two** completed matches, and
2. do they start **≥60%** of the matches they appear in?

Fail either and the club has already been playing without them, so the Dixon-Coles
rating — fitted on those very results — already prices the absence. Including them
subtracts the player twice.

**Result: 15 published absences, 15 excluded, 0 included.** Every named player has
**zero appearances** in the 81 fixtures this season:

```
Birmingham  Marc Leonard        Norwich     Mirko Topic, Gabriel Forsyth
Blackburn   Kargbo, Miller      Portsmouth  Umeh-Chibueze, Kosznovszky
Bristol City Luke McNally       QPR         Karamoko Dembele
Charlton    Joshua Edwards      Southampton Mads Roerslev
Derby       Patrick Agyemang    Swansea     Zeidane Inoussa
Millwall    Baker-Boaitey       West Ham    Tomas Soucek
```

Twelve further clubs have no published absence at all.

**So T5 = 0 is correct, and the prices are unchanged** — but it is now correct on
evidence rather than by assumption, which is the difference. This independently
reproduces the GW7 finding (62 of ~110 absentees with zero appearances).

⚠️ **The limit of this result: it says the published list contains no fresh injury, not
that no fresh injury exists.** A source that lists confirmed long-term absences will
under-report exactly the category T5 needs — the knock picked up in GW7 that keeps a
regular starter out on Saturday. Fifteen absences across 24 clubs is a thin list for a
Championship round. Confirmed team news lands about an hour before kick-off and would
settle it.

⚠️ A methodological note kept because it nearly produced a wrong answer: the first pass
used a surname-contains fallback when a full name did not match, and it returned three
hits — all three false. Millwall's Leonard was matched to Birmingham's Marc Leonard,
QPR's Edwards to Charlton's Joshua Edwards, Derby's Forsyth to Norwich's Gabriel Forsyth.
Matching is now full-name-within-club only.

### And the ratings still lag the table

GW7 measured the rank correlation between raw D-C net strength and 2026/27 PPG at
**0.334**. That is the documented source of large market disagreements in this league,
and it has not been fixed.

## Season context

Championship model selections are **0W-8L, −100% ROI** with +6.67% CLV (paper, not
staked) as of GW5, and the GW7 tracked slate returned **−69%** on seven selections that
all cleared 10% EV. Two rounds, both with double-digit EV qualifiers, both losing.

**This is the third such slate. The pattern is the EV screen, not the fixtures.**

## What would make this bettable

1. A **1X2 calibrator** — the single missing piece. `ml/football/backtest/walk_forward.py`
   would measure the draw tilt and produce one.
2. One live round of `elo_seeded` observed, not staked.
3. T5 rebuilt on appearance-filtered absences.
