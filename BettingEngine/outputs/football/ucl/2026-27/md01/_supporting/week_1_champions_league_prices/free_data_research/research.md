# Free UCL player-data research — 8 September 2026

Recommendation: ESPN as the primary historical player feed, UEFA and official club news for availability and projected/confirmed lineups, UEFA match PDFs for independent validation. This most closely matches the existing EPL/EFL implementation.

## What the existing model actually uses

The implemented train_starter_shadow.py uses Ridge residual corrections, eight-match rolling goals, assists, shots, shots on target, saves and minutes, aggregated by starting-player position group (GK/DEF/MID/ATT). It does not require player xG/xA to reproduce its current feature set. The build-spec's richer neural model is a plan, not the current trained implementation.

## Ranked free sources

1. ESPN: closest technical fit. An unauthenticated download from https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/summary?event=733620 succeeded. The unmodified existing parse_match function returned 45 roster rows and 22 starters, with player IDs, positions and all five current rolling-stat fields. Raw response and parsed CSV are stored alongside this report. This is one historical final, not a full-season or all-club coverage audit. The feed is a website endpoint; no supported public API guarantee or bulk-use licence was established.
2. UEFA team news: https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/ provides dated possible lineups, outs, doubts and suspensions. Use official club updates to resolve later changes. Possible lineups are not confirmed starters, and absence lists do not supply learned player values or expected minutes.
3. UEFA official reports: https://www.uefa.com/newsfiles/UCL/2025/2044466_SPS.pdf contains player played time, goals, shooting categories, fouls and cards. https://www.uefa.com/newsfiles/UCL/2026/2045975_LU.pdf provides tactical lineups. Good validation/fallback inputs, but PDF extraction and identity mapping are needed; the sampled player-summary report alone does not provide every ESPN model feature.
4. FotMob: free UCL player minutes verified at https://www.fotmob.com/en-GB/leagues/42/stats/season/28184/players/mins_played/champions-league-1000-players . Useful manual cross-check. The public league page https://www.fotmob.com/leagues/42/stats/champions-league/players explicitly prohibits systematic automated use, so do not select it as the unattended collection backbone.
5. Sofascore: https://www.sofascore.com/football/tournament/europe/uefa-champions-league/7 is a free competition results/statistics reference. No equivalent match-level parser or complete historical extraction was validated in this research; secondary candidate only.
6. StatsBomb/Hudl Open Data: https://github.com/hudl/open-data supplies selected competitions with event and lineup JSON. Free historical research resource, not evidence of complete current UCL coverage. Check the competition/match manifest before using any season; not the primary Week 1 feed.

## Implementation route matching EPL/EFL

Extend the existing ESPN collector's league mapping (currently eng.1, eng.2, eng.3 only) to UCL uefa.champions and participating clubs' domestic competitions. Audit coverage before downloading full archives, including less-covered domestic leagues. Reuse player IDs across competitions only after checking identity consistency. Domestic history is needed for recent form, minutes and transfers; UCL-only history is too sparse for the intended recent-player features.

Keep the existing CSV schema and eight-prior-match rolling logic. Reconcile ESPN fixture/team identities to UCL baseline IDs. Preserve missing-stat flags because the existing parser defaults missing numeric stats to zero. Its minutes are substitution-based estimates with 65/25-minute fallbacks and a default 90-minute match length: extra time, dismissals, stoppage time and unparsed substitutions require auditing before UCL training.

Archive dated UEFA/club availability evidence with publication and retrieval times; create early and final lineup snapshots separately. Estimate expected minutes from prior appearances and explicit assumptions; do not present them as observed pre-match facts. Player impact and replacement quality are model-derived quantities, not fields supplied by the news sites. Historical final lineups cannot reconstruct what an early forecast knew.

Train/evaluate residuals against the UCL baseline; do not claim Championship-trained coefficients are validated for UCL. Add UCL inference after collection and coverage validation. The existing ucl_player_shadow.py remains only a readiness checker.

## Tier coverage

T2: ESPN player history plus UEFA/club availability and lineups. T3: domestic/UCL match dates and player minutes support rest/workload, but do not automatically supply pressing or calibrated rotation/travel. T4: competition standings can support league-phase state; incentives still require model implementation. T5: not applicable to league-phase Week 1. T6: UEFA can identify referees; referee coefficients and weather remain separate inputs. T7 market odds and T8 confluence are not solved by player feeds. T1 missing cross-league opponent strength also remains a separate issue.

No shadow prices were produced in this research. The verified result is that an existing EPL/EFL parser can consume a real UCL ESPN sample without modification, and complementary free official sources exist.
