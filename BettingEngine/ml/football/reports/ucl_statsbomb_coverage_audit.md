# StatsBomb Open Data coverage audit

The official StatsBomb Open Data `competitions.json` lists men's Champions League seasons from 2010/11 through 2018/19, including 2011/12–2018/19. It does not list the 2024/25 or 2025/26 seasons required for our primary two-season validation. The data specification includes match, team, player and event fields suitable for building shot-based xG, but coverage—not model code—is the limiting factor.

## Decision

Use StatsBomb Open Data as a historical training/benchmark source where available, not as the sole source for the final two-season UCL test. For 2024/25–2025/26 we need either a licensed event provider or a second public shot/event source. Any blended xG file will carry `xg_source`, provider, season and coverage flags; provider values will not be silently mixed.

## Implementation route

1. Download and checksum the StatsBomb competition, match and event files for covered UCL seasons.
2. Build a common shot schema and train/validate the xG model on those events.
3. Acquire recent-season event data from a licensed provider or public source and map it to the same schema.
4. Compare provider xG against our shot model before replacing the current goals fallback.
5. Re-run the two-season walk-forward backtest only after coverage and timestamps pass the audit.

Source: https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json

## Recent-season candidate

FotMob publicly displays Champions League team/player xG and exposes match pages with xG fields, but its undocumented API is rate-limited and not a contractual historical archive. We will treat it as a candidate cross-check, not authoritative data, until we can archive complete 2024/25 and 2025/26 match-level records with retrieval timestamps. [FotMob UCL statistics](https://www.fotmob.com/leagues/42/stats/champions-league?season=2024-2025)
