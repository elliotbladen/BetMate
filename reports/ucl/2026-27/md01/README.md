# UCL matchday 1: opening, closing and $1 model selections

Research date: 15 September 2026. Normal model; 90-minute markets. One $1 bet per modelled match on its most likely 1X2 outcome, regardless of value. Six blocked fixtures are excluded, with no invented selections.

## 1X2 results

| Entry price | Bets | Wins | Staked | Returned | Profit | ROI |
|---|---:|---:|---:|---:|---:|---:|
| Pinnacle opening | 12 | 8 | $12.00 | $12.56 | $+0.56 | +4.67% |
| Pinnacle closing | 12 | 8 | $12.00 | $11.69 | $-0.31 | -2.55% |

Mean opening-to-close CLV: **+3.86%** using quoted odds, or **+0.99%** against the proportional margin-removed closing probabilities.

| Match | Pick | Model fair | Open | Close | CLV | Score | Open P/L | Close P/L |
|---|---|---:|---:|---:|---:|---|---:|---:|
| Club Brugge – Aston Villa | home | 2.57 | 2.640 | 2.480 | +6.45% | 2-3 | -1.000 | -1.000 |
| Borussia Dortmund – Villarreal | home | 1.67 | 1.794 | 1.741 | +3.04% | 3-2 | +0.794 | +0.741 |
| Porto – Manchester City | away | 2.25 | 1.794 | 1.654 | +8.47% | 0-2 | +0.794 | +0.654 |
| Real Madrid – Inter | away | 2.57 | 5.020 | 5.450 | -7.89% | 2-1 | -1.000 | -1.000 |
| Barcelona – Feyenoord | home | 1.46 | 1.139 | 1.082 | +5.26% | 5-1 | +0.139 | +0.082 |
| Liverpool – Atlético de Madrid | home | 1.63 | 1.746 | 1.769 | -1.30% | 2-1 | +0.746 | +0.769 |
| Paris Saint-Germain – Slovan Bratislava | home | 1.17 | 1.050 | 1.040 | +0.94% | 6-1 | +0.050 | +0.040 |
| Sporting CP – Galatasaray | home | 1.59 | 2.010 | 1.625 | +23.69% | 3-1 | +1.010 | +0.625 |
| Napoli – Arsenal | away | 1.93 | 1.877 | 1.704 | +10.15% | 0-1 | +0.877 | +0.704 |
| PSV Eindhoven – Shakhtar Donetsk | home | 1.97 | 1.420 | 1.513 | -6.12% | 1-1 | -1.000 | -1.000 |
| Bayern Munich – Bodo/Glimt | home | 1.28 | 1.152 | 1.080 | +6.64% | 5-0 | +0.152 | +0.080 |
| Slavia Prague – Lens | home | 1.82 | 2.850 | 2.940 | -3.06% | 2-3 | -1.000 | -1.000 |

## O/U 2.5: incomplete coverage

Only **three final frozen raw O/U predictions** were found: PSV Over (lost), Bayern Over (won), Slavia Under (lost). Nine final first-slate predictions explicitly withheld totals. The older audit contains totals from a failed/nonconverged baseline; those are not substituted. The previous top-level report incorrectly described 12 frozen totals prices.

The export has no exact 2.5 quotes for PSV or Bayern. Slavia has BetMGM Under 2.5 at the endpoints below. These do not establish a true market opener. A full totals ROI or opening-to-close CLV cannot be reported.

| Match | Model pick | Model fair | Outcome | Earliest available | Last available | Book |
|---|---|---:|---|---:|---:|---|
| PSV Eindhoven – Shakhtar Donetsk | over 2.5 | 1.328 | Lost | Missing | Missing | Missing |
| Bayern Munich – Bodo/Glimt | over 2.5 | 1.169 | Won | Missing | Missing | Missing |
| Slavia Prague – Lens | under 2.5 | 1.509 | Lost | 1.9803921568627452 | 2.3 | betmgm |

For the three saved totals selections, $3 would be staked. Total return equals the Bayern Over 2.5 entry odds, because the other two bets lose. Profit = Bayern odds − $3; ROI = (Bayern odds − 3) / 3. Its missing quote prevents a numeric answer. A combined 1X2 + totals ROI would therefore also be incomplete.

## Definitions and limits

- Decimal-odds CLV = opening odds / closing odds − 1. Positive means the opening bettor secured a higher payout. This is hypothetical opening-entry CLV, not evidence of bets actually placed.
- Margin-removed CLV = opening odds × closing fair probability − 1; closing fair probability = (1 / selection odds) / sum(1 / all three closing odds).
- Model edge = market odds / model fair odds − 1. It measures model-implied expected return, not CLV. All 36 1X2 outcomes and both entry comparisons are in `all_1x2_comparisons.csv`.
- ROI = net profit / total stake. A drawn match loses a home/away 1X2 bet. No commissions, bonuses, taxes or staking variation.
- Openers are Pinnacle-labelled home/away prices transcribed from the cited game pages. Opening timestamps and draw prices are unavailable. No no-vig opening probability is invented.
- Opening-price returns assume the later frozen model selections could be backed at those historical openers. Without opener timestamps, their availability after the model cutoff cannot be verified. This is a retrospective price benchmark, not an executable historical strategy.
- Closing quotes use Pinnacle rows in the timestamped export, not the page’s best-book summary: that summary sometimes compares a Pinnacle opener with another bookmaker’s close.
- The export was clamped to 8 September 07:35 UTC onward. First available quotes in it are not asserted to be opening quotes. The endpoint CSV retains quote times and market lines; snapshots after kickoff are excluded.
- No frozen model rerun or retrospective fit was used. Prices remain provisional research outputs with thin/stale team-history limitations. Twelve matches cannot establish long-run profitability.
- Missing selections: AEK–LASK, Lille–Betis, Stuttgart–Viking, Fenerbahçe–Roma, Como–Leipzig, Manchester United–Sabah.

## Sources and reproduction

- [UEFA final results](https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-league-phase-fixtures/)
- [The Odds Gap export schema and access limits](https://theoddsgap.com/data). `sources.json` records the request, returned window and original export hash. `quote_endpoints.csv` preserves the scoped numerical records used here.
- [Club Brugge opening quote and closing page](https://theoddsgap.com/odds/champions-league/aston-villa-vs-club-brugge)
- [Borussia Dortmund opening quote and closing page](https://theoddsgap.com/odds/champions-league/villarreal-vs-borussia-dortmund)
- [Porto opening quote and closing page](https://theoddsgap.com/odds/champions-league/manchester-city-vs-porto)
- [Real Madrid opening quote and closing page](https://theoddsgap.com/odds/champions-league/inter-milan-vs-real-madrid)
- [Barcelona opening quote and closing page](https://theoddsgap.com/odds/champions-league/feyenoord-vs-barcelona)
- [Liverpool opening quote and closing page](https://theoddsgap.com/odds/champions-league/atletico-madrid-vs-liverpool)
- [Paris Saint Germain opening quote and closing page](https://theoddsgap.com/odds/champions-league/sk-slovan-bratislava-vs-paris-saint-germain)
- [Sporting Lisbon opening quote and closing page](https://theoddsgap.com/odds/champions-league/galatasaray-vs-sporting-lisbon)
- [Napoli opening quote and closing page](https://theoddsgap.com/odds/champions-league/arsenal-vs-napoli)
- [PSV Eindhoven opening quote and closing page](https://theoddsgap.com/odds/champions-league/shakhtar-donetsk-vs-psv-eindhoven)
- [Bayern Munich opening quote and closing page](https://theoddsgap.com/odds/champions-league/bodo-glimt-vs-bayern-munich)
- [Slavia Praha opening quote and closing page](https://theoddsgap.com/odds/champions-league/rc-lens-vs-slavia-praha)

Run `python3 reports/ucl/2026-27/md01/calculate.py` from the repository root. Uses Python standard library only. Frozen model input hashes are recorded in `summary.json`.
