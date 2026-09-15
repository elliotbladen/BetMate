# EPL GW5 — EV screen and bet decision

**Entry rule:** ≥10% EV at the best available price · Market: Odds API (uk), 2026-09-15

## Recommendation: **no bets**

**Fifteen selections clear the 10% rule across ten matches.** That is the finding, not
the opportunity. A calibrated model does not find value in almost every game on the card;
a miscalibrated one does. This is the same shape as Championship GW7, where ten
selections cleared 10% EV, none was taken, and the slate went on to return −69% for the
tracked version.

## The EV screen

| fixture | model H/D/A | EV H | EV D | EV A | mdl O2.5 | mkt (no-vig) | EV O | EV U |
|---|---|---|---|---|---|---|---|---|
| Brentford v Chelsea | 39.0/23.4/37.7 | **+18.8%** | −6.6% | −12.6% | 77.8% | 63.5% | **+12.0%** | −44.4% |
| Tottenham v Aston Villa | 41.5/24.8/33.7 | −13.6% | −7.2% | **+31.4%** | 63.9% | 53.6% | **+16.3%** | −24.2% |
| Brighton v Arsenal | 27.7/24.3/48.0 | **+44.2%** | −0.6% | −16.0% | 58.5% | 53.9% | +6.0% | −12.1% |
| Everton v Ipswich ⚠️ | 55.9/24.4/19.7 | +2.3% | −2.3% | −5.6% | 52.2% | 54.8% | −6.0% | +4.2% |
| Newcastle v Hull ⚠️ | 58.9/21.3/19.8 | −2.2% | −4.3% | **+10.8%** | 67.3% | 57.8% | **+13.1%** | −24.9% |
| Nott'm Forest v Coventry ⚠️ | 49.7/26.8/23.5 | −15.4% | +9.9% | **+31.3%** | 50.5% | 53.2% | −7.5% | +2.9% |
| Bournemouth v Liverpool | 33.7/23.2/43.0 | +9.7% | −8.2% | −4.5% | 77.8% | 64.5% | **+12.0%** | −41.8% |
| Leeds v Crystal Palace | 46.9/24.8/28.3 | −13.2% | −1.9% | **+32.9%** | 67.3% | 54.3% | **+22.6%** | −29.5% |
| Man City v Sunderland | 68.2/20.0/11.8 | −8.6% | **+20.1%** | **+29.6%** | 54.3% | 60.3% | −12.1% | **+12.5%** |
| Fulham v Man United | 35.3/24.5/40.3 | **+28.7%** | −3.3% | −16.3% | 67.3% | 59.4% | +5.7% | −24.9% |

⚠️ = involves a promoted club (Ipswich, Hull, Coventry)

## Why none of them is a bet

### The Overs are one calibrator artefact plus a known bias

All five qualifying Overs come from three model numbers — 77.8%, 67.3%, 63.9% — and
67.3% is shared by three unrelated fixtures. On top of that the model runs **+6.2pp high
on P(Over) across the slate**. Both facts point the same way: the Over EVs are the bias
and the quantisation showing up as apparent value, not a read on the games.

**Do not bet EPL O/U 2.5 on this spine.** Same conclusion as the Championship, different
cause — Championship's calibrator has no resolution, EPL's has a systematic level error.

### Three of the loudest 1X2 edges ride promoted clubs

Nott'm Forest v Coventry (+31.3% on Coventry) and Newcastle v Hull (+10.8% on Hull) both
price a club the model has reset to exact league average with its current-season results
discarded. That is an unpriced input, not an edge — the standing instruction in CLAUDE.md
is to treat EV on Coventry / Hull / Ipswich as unpriced until the reset is fixed.

### Brighton +44.2% is the model disagreeing with a 28-book consensus by 20 points

Model has Brighton 27.7% to beat Arsenal; the de-vigged market has them near 18%. When
this engine and the market diverge that far, the documented prior is that **the model is
wrong** — the EPL spine has never been shown to beat the close.

### And T5 is only two-thirds audited

Confirmed absences were sourced for six clubs only. **Twelve clubs are UNAUDITED, not
injury-free:** Arsenal, Brighton, Chelsea, Coventry, Crystal Palace, Everton, Hull, Leeds,
Man United, Newcastle, Nott'm Forest, Sunderland. premierleague.com's injury table and
RotoWire are both JS-rendered or paywalled; only Fantasy Football Scout (14 Sep) served
its data.

**Every fixture on this card has at least one unaudited side.** Brighton v Arsenal — the
biggest edge on the slate — has *both* sides unaudited.

Confirmed absences used: Liverpool (Ekitike, Bradley, Leoni, Chiesa), Tottenham (Mudryk,
Simons, Odobert, Kulusevski, Porro, Tonali), Brentford (Furo, Collins, Jensen, van den
Berg, Dasilva, Milambo), Fulham (Cairney, Sessegnon), Ipswich (Taylor), Man City (Doku),
Aston Villa (Joao Gomes, suspended).

## What this slate is actually telling you

Fifteen qualifiers in ten games is a calibration report, not a bet list. The three faults
above — quantised totals calibrator, +6.2pp totals bias, promoted-club reset — are all
documented, all unfixed, and all still firing.

**The highest-value work is not pricing GW5. It is porting the Championship's
`new_team_reset_1x2: elo_seeded` fix to `epl.yaml`** — it was better in 10 of 10 seasons
there and EPL has three promoted clubs whose ratings are currently wiped to league
average every week.
