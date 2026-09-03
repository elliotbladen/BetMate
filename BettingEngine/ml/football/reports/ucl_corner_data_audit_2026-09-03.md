# UCL corner-data audit

The existing SofaScore collector was run against the mapped UCL event IDs.

- 342 matches returned full-match statistics.
- 2024/25: 156 matches.
- 2025/26: 186 matches.
- Both home and away corner fields are populated for the returned rows.
- The file also contains shots on target, xG, big chances, possession, fouls and cards.

The recent canonical fixture set has 378 matches. The remaining 36 were recovered from FotMob for xG and do not currently have a matched SofaScore event ID, so they are excluded from the corner track rather than being guessed. The corner model will therefore use a 342-match validated sample until those event mappings are repaired.

Source: SofaScore public event statistics endpoint (`/api/v1/event/{event_id}/statistics`). The endpoint is unofficial for automated research use; requests are rate-limited and the raw normalized output is retained at `data/ucl/xg/ucl_sofascore_match_stats.csv`.
