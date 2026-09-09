# Data-integrity lessons — how the numbers in this repo went wrong

Written 2026-09-09 from a single long session across BettingEngine and
RacingEngine. Every case below is real, from this repo, with the numbers.

The theme: **almost none of these were code bugs.** They were confident, plausible,
well-evidenced conclusions built on data that was quietly wrong — and in several
cases the checking tool was wrong too. If you are working here, assume the same
class of problem is present in whatever you are about to trust.

---

## 1. Two fields agreeing is not evidence either is right

**What happened.** The two NSW result sources disagreed on race distance for 362
races. To decide which was correct I tested each against the official clock:
RNSW's distance was physically consistent with RNSW's time in **362 of 362**
cases; racing-com in 89. Overwhelming. I "fixed" 362 distances.

Both fields came from the same wrong race. The RNSW importer had fetched a
**different meeting entirely** — 2024-04-13 Randwick returned the *2018* Queen
Elizabeth, with WINX and HARTNELL in a 2024 field. Distance and clock agreed
perfectly because they were both describing 2018.

**The check that caught it:** runner identity. Comparing *who actually ran*
between the two sources showed 437 of 1,006 shared races had a completely
different field.

**Rule.** Two fields from the same record corroborating each other tells you the
record is internally consistent, not that it is the right record. Verify identity
— the entity the row claims to describe — before trusting any field on it.

---

## 2. Validation that grades a model on its own arithmetic

**What happened.** I built a concordance gate: does a higher-rated horse finish
in front? It returned **0.84** for `form-first-v2.0`. Excellent — and meaningless.
A run figure is *derived* from that race's beaten margin
(`rating = race_strength − beaten_lengths × ppl`), so scoring it against that
race's finishing order recovers the arithmetic, not the skill.

Rebuilt on each horse's **prior** form, the honest number was **0.553**. A coin
flip is 0.500.

**Rule.** If a metric looks unexpectedly strong, check whether the thing being
scored already contains the answer. In racing specifically: never score a run
figure against its own race.

---

## 3. Gating a thing on a metric for a different thing

**What happened.** The rating engine was being promoted and rejected on
**top-pick strike rate and log loss** from a softmax fitted over the ratings.
That measures `ratings → probabilities → picks`. The probability conversion is the
*pricing* layer, which does not exist yet.

The build plan already said so — *"no profit claim is permitted from ratings
alone"* — and the symptom was recorded in the repo without being acted on:
*"temperature maxed the grid — the optimiser wants to flatten the ratings almost
entirely."* That is the fitted converter reporting that it is doing the work.

**Rule.** Match the metric to the artefact. A rating is judged on ordering,
repeatability, margin calibration and scale. Strike rate and ROI judge a price.
Using the wrong gate gives both false negatives and false positives.

---

## 4. A number with no baseline is not a result

**What happened.** Concordance 0.553 sounds like signal. Then:

| | concordance |
|---|---:|
| coin flip | 0.5000 |
| **official handicap mark (free)** | **0.5478** |
| form-first-v2.0 | 0.5527 |
| **last-start figure only** | **0.5706** |

The engine beats the free official mark by 0.005 — and is beaten by simply using
the horse's most recent figure with no blending at all.

**Rule.** Always score the trivial alternative on the same rows. "Do nothing",
"use the free public number", "use the last observation". A metric without them
cannot tell you whether the work is earning anything.

---

## 5. Leakage hides behind correctly-filtered dates

**What happened.** The franked-form predictive test filtered run **dates**
correctly — only runs before the race being predicted. But the run **values** were
built at `as_of_date`, and franking incorporates the beaten field's *later* form.
So a 2024 run's figure already knew what happened in 2025.

**Rule.** Filtering by date is not enough when the values are themselves derived
from later data. Ask when each *value* became knowable, not just when the event
happened. The fix is effective-dating: store when a revision became available and
use the figure as it stood.

---

## 6. Your verification tool is also code, and can also be wrong

Three in one session:

- **`racing_seed_status.py`** reported "LOCAL DB IS BEHIND — restore before doing
  racing work" after a cleanup removed 978 bad rows. It read a smaller row count
  as staleness. Following it would have restored over a full day's recovery.
- **A Playwright check** reported the Football Model tab was not deployed, six
  times. It enumerated `<button>` elements; the tabs do not match that way. The
  page had been live the whole time and I told the user it wasn't.
- **A grep-based audit** concluded the Sports Betting tab had no rows after
  2026-05-02. The regex only matched rows where `date:` immediately followed
  `id:`, missing most of a 512-row list.

**Rule.** When a check disagrees with reality, suspect the check. Confirm a
negative result a second way before reporting it.

---

## 7. Fallbacks fail silently and quietly poison data

- **`fetch_results.py`** fell back to an Internet Archive snapshot when the live
  host 503'd, and merged a **stale 10-row** version over the live season without
  saying anything. The real cause: `www.football-data.co.uk` was down while the
  bare domain served fine.
- **`rnsw.py`** reads the official race time from `seconds(row[16])` of a CSV
  layout that **no longer has a time column**. That fallback has been dead for an
  unknown period.
- An older importer cached ATC reports from a URL with **no year in it**, so
  every affected date silently fetched a different year's meeting. 108 dates.

**Rule.** A fallback must announce itself. Better: assert the fallback's output is
sane (row counts, date ranges, identity) before letting it overwrite anything.

---

## 8. Silent coverage gaps delete whole populations

NSW had **zero** official race clocks in the clean layer (0 of 1,388) while
Victoria had 99.8%. `rnsw-authorised` was missing from `SOURCE_PRIORITY`, and the
loader filters `if row["source"] in SOURCE_PRIORITY`, so every Racing NSW race was
dropped at load.

`performance-par-v2.0` only rates races that carry a clock. So **every Sydney
horse was invisible to the time-based rating** — which is why Autumn Glow, who
races exclusively in Sydney, had no runs in the top 10, and why Victorian G2/G3
runs dominated it. It looked like a model problem. It was a join.

**Rule.** Check coverage by every dimension that could partition the population —
state, source, class, season. `scripts/check_state_clock_coverage.py` exists for
exactly this and exits non-zero on a gap. Nothing was checking before.

---

## 9. Verify before switching a source, not after

The obvious fix for #8 was to promote `rnsw-authorised` above racing-com. Checked
first: on the 1,006 shared races RNSW has **fewer runners in 861** of them (10.5
vs 14.3 per race) and beaten lengths on **2.0%** of rows against **75.0%**.
Beaten lengths are what the collateral rating runs on — the swap would have been a
serious regression.

The right answer was a split: racing-com owns runner facts (identity, finishing
order, margins, weights); the official RNSW report owns race facts (distance,
clock), and only when identity verifies.

**Rule.** "Source A is authoritative" is rarely true field-by-field. Compare
per-field completeness before switching anything.

---

## 10. Records with holes are worse than no records

The NRL and AFL bet ledgers lost most of a season to silent gaps. The football
records were 115 flat files with three different naming conventions, and one
gameweek (EFL GW4, 1–2 Sep) had been played, never priced, never bet, never
reviewed — and nobody knew.

Fix pattern now in `outputs/football/`: a fixed set of artefacts per round, round
numbers **derived from played results** rather than a hand-kept list, and
`scripts/football_records_coverage.py` which exits non-zero on any gap. A round
with no qualifying bets needs an explicit `2_bets_none.md` — silence never counts
as satisfied.

**Rule.** Derive the expected set from ground truth, then assert completeness
against it. Absence must be recorded explicitly, never inferred from silence.

---

## The general shape

Every one of these produced a **confident, well-evidenced, wrong** answer:

- 362/362 agreement — from the same wrong race
- 0.84 concordance — from grading arithmetic against itself
- 18.2% strike rate — from a leaked future
- 87.9% coverage — from wrong-meeting donations
- "not deployed" ×6 — from a broken selector

Plausible corroboration is the failure mode, not obvious breakage. Before
reporting a number, ask: *what would make this look right while being wrong?*
Then go and check that specific thing.
