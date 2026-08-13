# macOS automation stocktake — 13 August 2026

## Replaced today

| Job | Previous state | Replacement |
|---|---|---|
| NRL price release | `com.bettingmodel.betmate-auto-price`; old `~/Betting_model`, exit 1 | `com.betmate.nrl-release`; active `BetMate/BettingEngine`; Monday 19:03 + Thursday 18:00; price, export, matrices, Baz publish |

The old plist was moved to `~/Library/LaunchAgents/com.bettingmodel.betmate-auto-price.plist.disabled` and is no longer loaded.

## Active and healthy

| Job | Purpose | Last observed state |
|---|---|---|
| `com.betmate.odds-snapshot-10min` | Current odds capture | exit 0 |
| `com.betmate.nrl-style-stats` | NRL style stats | exit 0 |
| `com.betmate.market-intelligence-refresh` | Market-intelligence refresh | exit 0 |
| `com.bettingengine.ht-nrl` / `ht-afl` | Half-time runner | NRL running / last exit 0 |
| `com.bettingengine.line-mover-*` | Line-movement pipeline | installed; has not yet run |

## Must migrate before relying on unattended data collection

These four jobs point at the retired `~/betmate-web` folder and all last exited 2, so they have not been collecting data:

| Legacy job | Required active replacement |
|---|---|
| `com.betmate.nrl-injuries-suspensions` | `BetMate/scrapers/nrl_injuries.py` |
| `com.betmate.nrl-emotional-flags` | `BetMate/scrapers/nrl_emotional.py` |
| `com.betmate.nrl-referees` | `BetMate/scrapers/nrl_referees.py` |
| `com.betmate.nrl-historical-odds` | `BetMate/scrapers/nrl_historical_results.py` (Playwright) |

The current release job tolerates refs being unannounced: its first price release publishes `TBC`; the Thursday release republish picks up the appointment when it exists.

## Retire after validating the current equivalents

| Legacy job | State | Reason |
|---|---|---|
| `com.bettingmodel.nrl-market-snapshot` | exit 0 | Writes to old `~/Betting_model`; current 10-minute odds snapshot is the active feed. |
| `com.bettingmodel.afl-market-snapshot` | exit 1 | Writes to old `~/Betting_model`; AFL snapshot path needs a current-engine release wrapper. |

## Recommendation

Build a second macOS launchd bundle for the four failed source collectors, then disable the two old `com.bettingmodel.*-market-snapshot` jobs. Do not copy the old `Betting_model` folder: it contains obsolete path/config assumptions rather than the active pipeline.
