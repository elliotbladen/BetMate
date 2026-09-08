# Researched UCL prices — 8 September 2026

9 provisional 1X2 prices from 12 fixtures. All use current researched form/rest and confirmed absences. These are research scenarios, not promoted full-tier production prices.

Decimal fair odds; H/D/A refers to home win/draw/away win over 90 minutes. Doubtful players are not assumed absent in the central price. Their alternative scenarios are in prices.json.

| Sydney date | Match | Home | Draw | Away |
|---|---|---:|---:|---:|
| 2026-09-09 | AEK Athens v LASK | — | — | — |
| 2026-09-09 | Club Brugge v Aston Villa | 2.57 | 3.30 | 3.24 |
| 2026-09-09 | Borussia Dortmund v Villarreal | 1.67 | 4.13 | 6.27 |
| 2026-09-09 | Porto v Manchester City | 3.66 | 3.54 | 2.25 |
| 2026-09-09 | Lille v Real Betis | — | — | — |
| 2026-09-09 | Real Madrid v Inter | 3.01 | 3.59 | 2.57 |
| 2026-09-10 | Barcelona v Feyenoord | 1.46 | 5.62 | 7.19 |
| 2026-09-10 | Stuttgart v Viking | — | — | — |
| 2026-09-10 | Liverpool v Atlético de Madrid | 1.63 | 4.46 | 6.11 |
| 2026-09-10 | Paris Saint-Germain v Slovan Bratislava | 1.17 | 10.97 | 19.11 |
| 2026-09-10 | Sporting CP v Galatasaray | 1.59 | 4.74 | 6.21 |
| 2026-09-10 | Napoli v Arsenal | 4.22 | 4.07 | 1.93 |

## Model and coverage

The fit converged in 680 iterations and 224575 evaluations after explicit club-ID reconciliation. The likelihood and default tier coefficients were retained. Normalization now preserves fitted goal rates with base-rate compensation 0.567007; legacy production callers retain their prior version. The cached fit uses 1997 UCL matches through 2026-05-30 18:00:00+00:00.

Current domestic form/rest and sourced availability enter the price explicitly. The injury method is the legacy football positional prior, not a trained UCL player valuation. Returning, doubtful and disputed players are scenario inputs. Replacement quality and expected minutes remain unmodelled; long-term absences can overlap with historical team strength. This limits confidence in large changes.

Verified referee names do not supply referee scoring coefficients. PPDA, calibrated travel/rotation/weather and confluence remain missing; current bookmaker quotes were not captured. No EV or bet recommendation is generated. The player shadow is not promoted.

AEK–LASK, Lille–Betis and Stuttgart–Viking still lack comparable baseline strength for an opponent. Recent domestic records were researched for them, but a few domestic results cannot replace the missing cross-league model.

Totals are withheld: the separate U/O market model is not ready to consume these live tiers. Raw shared-score-matrix totals are not substituted for that model.

## Current domestic input audit

| Team | Points / games observed | Latest competitive match | Rest days |
|---|---:|---|---:|
| AEK Athens | 7 / 3 | 2026-09-05 | 3 |
| LASK | 15 / 5 | 2026-09-05 | 3 |
| Club Brugge | 12 / 5 | 2026-09-04 | 4 |
| Aston Villa | 1 / 3 | 2026-09-05 | 3 |
| Borussia Dortmund | 6 / 2 | 2026-09-05 | 3 |
| Villarreal | 2 / 4 | 2026-09-05 | 3 |
| Porto | 15 / 5 | 2026-09-04 | 4 |
| Manchester City | 9 / 3 | 2026-09-05 | 3 |
| Lille | 7 / 3 | 2026-09-03 | 5 |
| Real Betis | 9 / 4 | 2026-09-04 | 4 |
| Real Madrid | 9 / 4 | 2026-09-04 | 4 |
| Inter | 9 / 3 | 2026-09-05 | 3 |
| Barcelona | 12 / 4 | 2026-09-06 | 3 |
| Feyenoord | 11 / 5 | 2026-09-05 | 4 |
| Stuttgart | 3 / 2 | 2026-09-04 | 5 |
| Viking | 10 / 5 | 2026-09-04 | 5 |
| Liverpool | 5 / 3 | 2026-09-04 | 5 |
| Atlético de Madrid | 7 / 4 | 2026-09-05 | 4 |
| Paris Saint-Germain | 2 / 3 | 2026-09-04 | 5 |
| Slovan Bratislava | 9 / 5 | 2026-09-05 | 4 |
| Sporting CP | 13 / 5 | 2026-09-05 | 4 |
| Galatasaray | 10 / 4 | 2026-09-04 | 5 |
| Napoli | 3 / 3 | 2026-09-05 | 4 |
| Arsenal | 9 / 3 | 2026-09-06 | 3 |

Short early-season form samples use a neutral 1.5-point prior for each unplayed slot to fit the existing five-game feature; no match outcomes are invented. Form is league-only; rest uses the latest verified competitive club match.

## Sources

- [UEFA team news](https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/)
- [Football-Data domestic results](https://www.football-data.co.uk/downloadm.php)
- [Slovan official results](https://www.skslovan.com/zapasy/index.php?season=202627)
- [Real Madrid training](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/entrenamientos/el-equipo-se-esta-entrenando-07-09-2026)
- [Real Madrid press conference](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/ruedas-de-prensa/mourinho-07-09-2026)
- [Dimarco update](https://www.gazzetta.it/en/football/teams/inter/news/07-09-2026/dimarco-injury-wing-back-misses-real-madrid-clash.shtml)
