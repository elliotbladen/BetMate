# Week 1 Champions League shadow player rating

Saved from the completed UCL-trained player-shadow run. These are research-only 90-minute fair prices using projected lineups; no betting approval or production promotion is implied.

## Normal/player-shadow disagreements

The comparison rule is the most probable 1X2 result after each model's probabilities are applied.

| Match | Normal selection | Player-shadow selection | Normal fair odds | Shadow fair odds |
|---|---|---|---|---|
| Real Madrid v Inter | Inter | Real Madrid | Madrid 3.01 / Draw 3.59 / Inter 2.57 | Madrid 2.59 / Draw 3.59 / Inter 2.99 |

This is the only selection disagreement among the nine priceable fixtures. The shadow moves Real Madrid from 33.2% to 38.6% and Inter from 38.9% to 33.4%; the draw remains about 27.8%.

The other nine priceable games retain the same most-probable outcome:

- Club Brugge v Aston Villa — Club Brugge
- Borussia Dortmund v Villarreal — Dortmund
- Porto v Manchester City — Manchester City
- Barcelona v Feyenoord — Barcelona
- Liverpool v Atlético de Madrid — Liverpool
- Paris Saint-Germain v Slovan Bratislava — PSG
- Sporting CP v Galatasaray — Sporting
- Napoli v Arsenal — Arsenal

AEK Athens v LASK, Lille v Real Betis and Stuttgart v Viking are blocked in both models because the normal UCL baseline has no comparable opponent strength. They have no player-shadow selection.

The full source files are `prices.json`, `prices.csv`, `projected_player_events.csv`, and `source_report.md` in this folder. `source_report.md` includes the holdout evaluation, tier coverage, input limitations and per-player audit.
