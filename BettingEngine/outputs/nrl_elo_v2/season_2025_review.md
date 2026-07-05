# NRL Elo v2 Labels - 2025 Season

Generated from match stats first, with report snippets attached as context.

## Summary

- Matches reviewed: 213
- Elo v2 mismatch flags: 37
- High confidence: 14
- Medium confidence: 13
- Low confidence: 10
- Adjustment types: close_game_tension=9, margin_exaggeration=4, stat_reversal=24
- Default adjustment for flags: reduce winner reward and loser penalty
- Starting experiment multipliers: 0.50 for stat reversal, 0.70 for margin exaggeration, 0.80 for close/report tension

## Flagged Matches

| Round | Match | Result | Type | Hard done by | Lucky winner | Conf | Severity | Notes |
| ---: | --- | ---: | --- | --- | --- | --- | ---: | --- |
| 1 | South Sydney Rabbitohs vs Dolphins | 16-14 | stat_reversal | Dolphins | South Sydney Rabbitohs | medium | 14.87 | run_metres +102; tackle_busts +19; tackledOpp20 +3; territory +33; errors +4; inCompleteSets +6; missed_tackles -19. Report context: injury |
| 2 | St. George Illawarra Dragons vs South Sydney Rabbitohs | 24-25 | stat_reversal | St. George Illawarra Dragons | South Sydney Rabbitohs | high | 22.55 | line_breaks +3; try_assists +3; run_metres +167; tackle_busts +12; tackledOpp20 -4; complete_sets -6; missed_tackles -12. Report context: bunker / controversial / no try / penalty try |
| 3 | Melbourne Storm vs Penrith Panthers | 30-24 | stat_reversal | Penrith Panthers | Melbourne Storm | high | 28.17 | line_breaks +3; tackle_busts +5; tackledOpp20 +27; forced_drop_outs +3; possession_percentage +6; territory +7.9; complete_sets +10; errors -4; inCompleteSets -5. Report context: injury / late |
| 4 | Sydney Roosters vs Gold Coast Titans | 12-30 | stat_reversal | Sydney Roosters | Gold Coast Titans | medium | 16.91 | line_breaks +5; tackle_busts +28; tackledOpp20 +16; territory +14.2; complete_sets -9; errors +5; inCompleteSets +8; penalties_conceded +3; missed_tackles -28 |
| 4 | St. George Illawarra Dragons vs Melbourne Storm | 14-8 | stat_reversal | Melbourne Storm | St. George Illawarra Dragons | medium | 13.28 | run_metres +114; tackle_busts +8; tackledOpp20 +12; territory +19.1; errors +5; penalties_conceded -5; missed_tackles -8. Report context: late |
| 5 | Canberra Raiders vs Cronulla-Sutherland Sharks | 24-20 | close_game_tension | Cronulla-Sutherland Sharks | Canberra Raiders | low | 10.99 | run_metres +202; tackle_busts -12; tackledOpp20 +12; territory +14.5; complete_sets +6; penalties_conceded -5; missed_tackles +12 |
| 5 | Brisbane Broncos vs Wests Tigers | 46-24 | margin_exaggeration | Wests Tigers | Brisbane Broncos | low | 9.12 | tackle_busts -10; territory -16.3; complete_sets +6; errors -5; penalties_conceded -3; missed_tackles +10 |
| 6 | Dolphins vs Penrith Panthers | 30-12 | margin_exaggeration | Penrith Panthers | Dolphins | low | 8.44 | line_breaks -3; run_metres +139; post_contact_metres +141; tackle_busts -15; tackledOpp20 +27; forced_drop_outs +3; possession_percentage +8; territory +25.9; complete_sets +3. Report context: bunker / sin bin |
| 7 | New Zealand Warriors vs Brisbane Broncos | 20-18 | close_game_tension | Brisbane Broncos | New Zealand Warriors | low | 9.33 | run_metres -102; tackle_busts +8; tackledOpp20 -26; complete_sets -4; penalties_conceded +6; missed_tackles -8 |
| 8 | Wests Tigers vs Cronulla-Sutherland Sharks | 20-18 | close_game_tension | Cronulla-Sutherland Sharks | Wests Tigers | low | 7.72 | tackle_busts +3; tackledOpp20 +5; complete_sets -9; errors +6; inCompleteSets +3; penalties_conceded +3; missed_tackles -3 |
| 9 | New Zealand Warriors vs North Queensland Cowboys | 30-26 | stat_reversal | North Queensland Cowboys | New Zealand Warriors | high | 20.51 | run_metres +283; post_contact_metres +166; tackle_busts +13; tackledOpp20 +22; possession_percentage +12; territory +24.7; complete_sets -4; errors +4; inCompleteSets +6 |
| 9 | Wests Tigers vs St. George Illawarra Dragons | 34-28 | stat_reversal | St. George Illawarra Dragons | Wests Tigers | high | 39.21 | line_breaks +9; run_metres +100; tackle_busts +28; tackledOpp20 +6; territory +7.5; missed_tackles -28 |
| 10 | South Sydney Rabbitohs vs Brisbane Broncos | 22-14 | stat_reversal | Brisbane Broncos | South Sydney Rabbitohs | high | 27.15 | line_breaks +4; run_metres +250; post_contact_metres +105; tackle_busts +13; tackledOpp20 +10; forced_drop_outs +5; territory +12.9; complete_sets -3; errors +3. Report context: injury / late |
| 10 | St. George Illawarra Dragons vs New Zealand Warriors | 14-15 | stat_reversal | St. George Illawarra Dragons | New Zealand Warriors | medium | 13.39 | line_breaks +4; tackledOpp20 -5; territory +18.6; complete_sets -3; errors +5; inCompleteSets +7. Report context: comeback / late |
| 11 | Canterbury-Bankstown Bulldogs vs Sydney Roosters | 24-20 | close_game_tension | Sydney Roosters | Canterbury-Bankstown Bulldogs | low | 10.54 | tackle_busts +10; tackledOpp20 -19; forced_drop_outs +3; complete_sets -3; errors +8; inCompleteSets +4; missed_tackles -10 |
| 11 | Brisbane Broncos vs St. George Illawarra Dragons | 26-30 | stat_reversal | Brisbane Broncos | St. George Illawarra Dragons | high | 16.8 | line_breaks +4; run_metres +201; territory +10.5; complete_sets -8; errors +5; inCompleteSets +9. Report context: comeback / controversial |
| 12 | Parramatta Eels vs Manly-Warringah Sea Eagles | 30-10 | margin_exaggeration | Manly-Warringah Sea Eagles | Parramatta Eels | low | 9.91 | try_assists -3; tackledOpp20 +17; territory +18.7; errors -3 |
| 13 | Penrith Panthers vs Parramatta Eels | 18-10 | close_game_tension | Parramatta Eels | Penrith Panthers | low | 7.88 | run_metres -202; post_contact_metres -81; tackle_busts +6; tackledOpp20 -6; territory -21.3; penalties_conceded -3; missed_tackles -6 |
| 14 | Newcastle Knights vs Manly-Warringah Sea Eagles | 26-22 | stat_reversal | Manly-Warringah Sea Eagles | Newcastle Knights | high | 20.87 | run_metres +111; post_contact_metres +95; tackledOpp20 +16; possession_percentage +6; territory +10.3; complete_sets +7; errors -3; inCompleteSets -5; penalties_conceded -3 |
| 15 | Newcastle Knights vs Sydney Roosters | 8-12 | stat_reversal | Newcastle Knights | Sydney Roosters | medium | 14.85 | run_metres +154; tackle_busts +7; tackledOpp20 +29; possession_percentage +10; territory +25.8; complete_sets +4; errors +4; penalties_conceded -3; missed_tackles -7. Report context: head knock / injury |
| 16 | Wests Tigers vs Canberra Raiders | 12-16 | stat_reversal | Wests Tigers | Canberra Raiders | medium | 13.09 | run_metres +345; post_contact_metres +149; tackledOpp20 +23; territory +19.1; complete_sets +3; errors +3; inCompleteSets +6 |
| 16 | Dolphins vs Newcastle Knights | 20-26 | stat_reversal | Dolphins | Newcastle Knights | high | 17.09 | line_breaks +4; run_metres +177; tackle_busts -18; tackledOpp20 +21; possession_percentage +6; territory +21.5; penalties_conceded -4; missed_tackles +18. Report context: controversial / no try |
| 17 | Gold Coast Titans vs North Queensland Cowboys | 24-30 | stat_reversal | Gold Coast Titans | North Queensland Cowboys | medium | 11.6 | run_metres +97; tackle_busts +18; tackledOpp20 +5; forced_drop_outs -3; possession_percentage +6; territory +11.8; missed_tackles -18. Report context: comeback |
| 18 | Sydney Roosters vs Wests Tigers | 28-30 | close_game_tension | Sydney Roosters | Wests Tigers | low | 9.44 | run_metres -98; tackle_busts +6; tackledOpp20 +13; errors +3; inCompleteSets +4; missed_tackles -6 |
| 19 | St. George Illawarra Dragons vs Sydney Roosters | 24-31 | close_game_tension | St. George Illawarra Dragons | Sydney Roosters | medium | 13.06 | run_metres +149; tackle_busts -7; tackledOpp20 +17; complete_sets +4; inCompleteSets +3; penalties_conceded -3; missed_tackles +7. Report context: injury / sin bin |
| 19 | North Queensland Cowboys vs Canterbury-Bankstown Bulldogs | 8-12 | stat_reversal | North Queensland Cowboys | Canterbury-Bankstown Bulldogs | low | 10.21 | line_breaks +3; run_metres -120; post_contact_metres -86; tackle_busts +29; tackledOpp20 -6; territory -16.1; errors +3; inCompleteSets +6; penalties_conceded -4 |
| 20 | Penrith Panthers vs South Sydney Rabbitohs | 30-10 | margin_exaggeration | South Sydney Rabbitohs | Penrith Panthers | medium | 9.11 | line_breaks -3; run_metres -177; post_contact_metres +105; tackle_busts -9; tackledOpp20 +4; errors -10; inCompleteSets -6; missed_tackles +9. Report context: head knock / injury / late |
| 21 | Sydney Roosters vs Melbourne Storm | 30-34 | close_game_tension | Sydney Roosters | Melbourne Storm | medium | 13.26 | tackle_busts +8; tackledOpp20 +4; territory +13.2; inCompleteSets +3; missed_tackles -8. Report context: injury / late |
| 21 | Brisbane Broncos vs Parramatta Eels | 20-22 | close_game_tension | Brisbane Broncos | Parramatta Eels | medium | 11.57 | run_metres +197; post_contact_metres +88; tackle_busts +5; tackledOpp20 -14; possession_percentage -6; missed_tackles -5. Report context: bunker |
| 22 | New Zealand Warriors vs Dolphins | 18-20 | stat_reversal | New Zealand Warriors | Dolphins | medium | 13.27 | run_metres +228; post_contact_metres +152; tackledOpp20 +24; territory +13.7; complete_sets +4. Report context: injury |
| 22 | Gold Coast Titans vs Penrith Panthers | 26-30 | stat_reversal | Gold Coast Titans | Penrith Panthers | high | 16.78 | tackle_busts +22; tackledOpp20 +20; territory -5.6; complete_sets +4; inCompleteSets -4; penalties_conceded -6; missed_tackles -22. Report context: late |
| 23 | Gold Coast Titans vs South Sydney Rabbitohs | 18-20 | stat_reversal | Gold Coast Titans | South Sydney Rabbitohs | high | 24.09 | run_metres +258; post_contact_metres +109; tackle_busts +26; tackledOpp20 +15; territory +20.6; missed_tackles -26 |
| 24 | Penrith Panthers vs Melbourne Storm | 18-22 | stat_reversal | Penrith Panthers | Melbourne Storm | high | 17.31 | run_metres +224; tackle_busts +6; territory +26.7; errors +6; missed_tackles -6. Report context: injury |
| 24 | South Sydney Rabbitohs vs Parramatta Eels | 20-16 | stat_reversal | Parramatta Eels | South Sydney Rabbitohs | medium | 15.69 | run_metres +306; post_contact_metres +113; tackle_busts +10; tackledOpp20 +10; territory +27.7; complete_sets -7; errors +4; inCompleteSets +5; penalties_conceded -5 |
| 25 | Melbourne Storm vs Canterbury-Bankstown Bulldogs | 20-14 | stat_reversal | Canterbury-Bankstown Bulldogs | Melbourne Storm | high | 25.57 | line_breaks +4; run_metres +347; tackle_busts +5; tackledOpp20 +24; possession_percentage +10; territory +33; errors +5; inCompleteSets +6; penalties_conceded +3. Report context: bunker / late |
| 26 | New Zealand Warriors vs Parramatta Eels | 22-26 | stat_reversal | New Zealand Warriors | Parramatta Eels | high | 29.01 | run_metres +302; post_contact_metres +226; tackle_busts +18; tackledOpp20 +20; possession_percentage +10; territory +29; complete_sets +4; inCompleteSets +3; missed_tackles -18. Report context: bunker / controversial / late |
| 27 | Manly-Warringah Sea Eagles vs New Zealand Warriors | 27-26 | stat_reversal | New Zealand Warriors | Manly-Warringah Sea Eagles | high | 31.32 | line_breaks +4; run_metres +131; tackle_busts +14; tackledOpp20 +4; errors -4; inCompleteSets -3; missed_tackles -14 |

## Method

A stat dominance score is calculated from score-independent match stats: line breaks, try assists, run metres, post-contact metres, tackle busts, opposition-20 tackles, forced dropouts, possession, territory, complete sets, errors, incomplete sets, penalties conceded, missed tackles and sin bins.

A game is an adjustment candidate when the scoreboard winner is opposite to the stat dominance winner, when the margin looks inflated relative to the stat profile, or when a close result has weak winner support plus report context. Within each round, the top candidate is flagged above threshold and a second candidate is allowed when its score is also strong.

Reports are not used to create the stat score. They only add context terms such as controversial, bunker, penalty try, sin bin, injury, HIA, no try, late, intercept, against the run of play or comeback.
