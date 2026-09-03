# NFL valid paper-market quote schema

Each captured bookmaker quote must contain:

| Field | Requirement |
|---|---|
| `game_id` | Canonical `YYYY_WW_AWAY_HOME` identity |
| `bookmaker` | Non-empty named bookmaker |
| `captured_at_utc` | Timezone-aware ISO-8601 timestamp |
| `stage` | `first_obtainable`, `decision`, or `close` |
| `home_spread` | Negative when the home team is favourite |
| `home_spread_decimal` | Actual available decimal price |
| `away_spread_decimal` | Actual available decimal price |
| `total_line` | Available points total |
| `over_decimal` | Actual available decimal price |
| `under_decimal` | Actual available decimal price |
| `home_h2h_decimal` | Home moneyline decimal price |
| `away_h2h_decimal` | Away moneyline decimal price |
| `source` | API/feed identity or source URL |

Quotes missing bookmaker, timestamp or actual prices cannot be used for CLV or
ROI. Corrections must be appended with their own timestamp; frozen rows are not
silently overwritten.

