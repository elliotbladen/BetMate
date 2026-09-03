# AFL 2026 Finals Week 2 — provisional Monte Carlo pricing

Priced: 2026-09-02 (Australia/Brisbane)  
Simulation: 100,000 runs per game, seed 20260902

## Monte Carlo prices

| Game | Model margin | H2H fair price | Model total | Market line | Market total |
|---|---:|---:|---:|---:|---:|
| Fremantle v Hawthorn | Fremantle -15.2 | Fremantle $1.48 / Hawthorn $3.08 | 184.7 | Fremantle -13.5 | 162.5 |
| Geelong v Carlton | Geelong -19.3 | Geelong $1.43 / Carlton $3.33 | 185.4 | Geelong -6.5 | 168.5 |
| Sydney v Brisbane | Sydney -10.8 | Sydney $1.70 / Brisbane $2.43 | 214.4 | Brisbane -24.5 | 187.5 |
| Adelaide v Western Bulldogs | Adelaide -41.9 | Adelaide $1.15 / Bulldogs $7.61 | 177.6 | Adelaide -15.5 | 168.5 |

## Market comparison

| Selection | Captured odds | MC probability | EV | Status |
|---|---:|---:|---:|---|
| Fremantle–Hawthorn Over 162.5 | $1.87 | 77.3% | +44.6% | Large totals edge; verify line/weather |
| Adelaide -15.5 | $1.90 | 76.5% | +45.4% | Qualifies, but models disagree by 17 points |
| Geelong–Carlton Over 168.5 | $1.90 | 70.4% | +33.8% | Qualifies; rules/ML totals gap is large |
| Adelaide H2H | $1.42 | 86.9% | +23.4% | Qualifies |
| Geelong -6.5 | $1.91 | 62.3% | +18.9% | Qualifies |
| Geelong H2H | $1.67 | 70.0% | +16.9% | Qualifies |
| Adelaide–Bulldogs Over 168.5 | $1.86 | 62.2% | +15.7% | Qualifies; rules/ML totals gap is large |
| Sydney +24.5 | $1.90 | 82.9% | +57.4% | **Hard review/veto pending lineup-model diagnosis** |
| Sydney H2H | $3.72 | 58.9% | +118.9% | **Hard review/veto; model and market are irreconcilable** |

The Sydney prices are not approved betting signals. Sydney's confirmed absences
include Heeney, Warner, Blakey, Jordon, McInerney, Ladhams and King, while the
bookmaker makes Brisbane a 24.5-point favourite. The AFL T5 cap and historical
team-strength inputs do not fully represent a disruption of that scale.

## Method and coverage

- Centre: frozen finals blend of 75% ML and 25% rules for margin; rules-only
  totals. H2H is derived coherently from the simulated margin distribution.
- Error distribution: paired margin and total residuals from 216 untouched 2025
  games, preserving their empirical dependence.
- Disagreement: additional zero-mean uncertainty proportional to the rules/ML
  gap; it widens the distribution rather than pulling it toward the market.
- Availability: explicit play/out scenarios for current Test/TBC players.
- T1, T3, T4, T5, T7 and T8 used current or refreshed data. T2 used the latest
  complete 18-team snapshot (Round 23) and is two round labels old. T6 was
  manually reviewed and left neutral because no asymmetric evidence-backed flag
  was found. Seven of eight tiers were substantively populated/reviewed.
- This Monte Carlo layer is provisional and has not passed a finals-specific
  walk-forward validation. It is decision support, not an automatic betting rule.

Market snapshot: Sportsbet, captured 2026-09-02 at approximately 09:37 AEST.
