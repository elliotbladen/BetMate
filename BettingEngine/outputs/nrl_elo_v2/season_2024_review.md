# NRL Elo v2 Labels - 2024 Season

Generated from match stats first, with report snippets attached as context.

## Summary

- Matches reviewed: 213
- Elo v2 mismatch flags: 36
- High confidence: 11
- Medium confidence: 12
- Low confidence: 13
- Adjustment types: close_game_tension=14, margin_exaggeration=1, report_context_tension=1, stat_reversal=20
- Default adjustment for flags: reduce winner reward and loser penalty
- Starting experiment multipliers: 0.50 for stat reversal, 0.70 for margin exaggeration, 0.80 for close/report tension

## Flagged Matches

| Round | Match | Result | Type | Hard done by | Lucky winner | Conf | Severity | Notes |
| ---: | --- | ---: | --- | --- | --- | --- | ---: | --- |
| 1 | New Zealand Warriors vs Cronulla-Sutherland Sharks | 12-16 | stat_reversal | New Zealand Warriors | Cronulla-Sutherland Sharks | high | 27.16 | run_metres +360; post_contact_metres +106; tackle_busts +10; tackledOpp20 +28; forced_drop_outs +5; possession_percentage +8; territory +32.7; complete_sets +8; missed_tackles -10 |
| 1 | Melbourne Storm vs Penrith Panthers | 8-0 | stat_reversal | Penrith Panthers | Melbourne Storm | high | 24.38 | run_metres +140; tackle_busts +13; tackledOpp20 +25; forced_drop_outs +4; possession_percentage +8; territory +38.1; complete_sets +6; penalties_conceded +3; missed_tackles -13 |
| 2 | Melbourne Storm vs New Zealand Warriors | 30-26 | close_game_tension | New Zealand Warriors | Melbourne Storm | low | 8.45 | line_breaks -3; run_metres +118; post_contact_metres +89; tackle_busts -7; tackledOpp20 +5; forced_drop_outs -3; territory +31.2; penalties_conceded -4; missed_tackles +7 |
| 3 | Newcastle Knights vs Melbourne Storm | 14-12 | close_game_tension | Melbourne Storm | Newcastle Knights | medium | 11.71 | tackledOpp20 +5; territory +13.4; inCompleteSets +3 |
| 4 | St. George Illawarra Dragons vs Manly-Warringah Sea Eagles | 20-12 | close_game_tension | Manly-Warringah Sea Eagles | St. George Illawarra Dragons | medium | 12.89 | run_metres +245; post_contact_metres +107; tackle_busts -16; tackledOpp20 +13; possession_percentage +8; territory +24.7; missed_tackles +16. Report context: bunker / controversial / no try |
| 4 | Parramatta Eels vs Wests Tigers | 16-17 | stat_reversal | Parramatta Eels | Wests Tigers | medium | 15.81 | run_metres +216; tackledOpp20 +11; possession_percentage +6; territory +29.7; errors +3; penalties_conceded -7 |
| 6 | Parramatta Eels vs North Queensland Cowboys | 27-20 | close_game_tension | North Queensland Cowboys | Parramatta Eels | low | 7.97 | tackle_busts -4; tackledOpp20 -12; territory -6.8; penalties_conceded +3; missed_tackles +4 |
| 7 | Sydney Roosters vs Melbourne Storm | 12-18 | report_context_tension | Sydney Roosters | Melbourne Storm | low | 8.8 | line_breaks -4; tackle_busts -12; tackledOpp20 -5; territory +14.6; inCompleteSets -3; penalties_conceded +3; missed_tackles +12. Report context: injury / late |
| 8 | New Zealand Warriors vs Gold Coast Titans | 24-27 | stat_reversal | New Zealand Warriors | Gold Coast Titans | medium | 10.62 | run_metres +274; tackle_busts -5; tackledOpp20 +26; territory +38.7; missed_tackles +5. Report context: late |
| 8 | North Queensland Cowboys vs Penrith Panthers | 20-26 | stat_reversal | North Queensland Cowboys | Penrith Panthers | high | 29.65 | run_metres +166; post_contact_metres +120; tackle_busts +7; tackledOpp20 +28; possession_percentage +10; territory +18; complete_sets +9; missed_tackles -7. Report context: comeback / late |
| 9 | Manly-Warringah Sea Eagles vs Canberra Raiders | 24-26 | close_game_tension | Manly-Warringah Sea Eagles | Canberra Raiders | low | 9.75 | tackle_busts -4; tackledOpp20 +3; territory -17.8; inCompleteSets +5; penalties_conceded -5; missed_tackles +4 |
| 9 | Gold Coast Titans vs Melbourne Storm | 20-22 | stat_reversal | Gold Coast Titans | Melbourne Storm | high | 24.17 | post_contact_metres +116; tackle_busts +32; tackledOpp20 +3; possession_percentage +8; territory +5.7; penalties_conceded +3; missed_tackles -32. Report context: late |
| 10 | Dolphins vs Manly-Warringah Sea Eagles | 30-24 | close_game_tension | Manly-Warringah Sea Eagles | Dolphins | low | 10.7 | run_metres -81; tackledOpp20 +20; territory -6.9 |
| 11 | Canberra Raiders vs Canterbury-Bankstown Bulldogs | 24-20 | stat_reversal | Canterbury-Bankstown Bulldogs | Canberra Raiders | high | 20.01 | run_metres +192; tackle_busts -5; tackledOpp20 +19; possession_percentage +8; territory +13.8; inCompleteSets +3; penalties_conceded -4; missed_tackles +5. Report context: injury / sin bin |
| 12 | Brisbane Broncos vs Gold Coast Titans | 34-36 | close_game_tension | Brisbane Broncos | Gold Coast Titans | medium | 12.11 | line_breaks +4; run_metres -139; tackledOpp20 -6; possession_percentage -18; complete_sets -8; errors +5; inCompleteSets +4 |
| 13 | Dolphins vs Canberra Raiders | 25-26 | close_game_tension | Dolphins | Canberra Raiders | low | 8.69 | line_breaks -3; post_contact_metres -142; tackle_busts -11; tackledOpp20 +15; territory +18.1; complete_sets +5; errors -5; inCompleteSets -3; penalties_conceded +4 |
| 14 | Canterbury-Bankstown Bulldogs vs Parramatta Eels | 22-18 | close_game_tension | Parramatta Eels | Canterbury-Bankstown Bulldogs | low | 8.46 | line_breaks -4; post_contact_metres +88; tackle_busts -8; tackledOpp20 +11; possession_percentage +6; territory +19.7; complete_sets +4; penalties_conceded -5; missed_tackles +8 |
| 15 | Wests Tigers vs Gold Coast Titans | 18-10 | stat_reversal | Gold Coast Titans | Wests Tigers | low | 9.51 | line_breaks +4; run_metres +233; tackle_busts +13; tackledOpp20 -10; territory +6.9; complete_sets -7; errors +7; inCompleteSets +6; missed_tackles -13 |
| 16 | Wests Tigers vs Canberra Raiders | 48-24 | stat_reversal | Canberra Raiders | Wests Tigers | low | 8.78 | line_breaks +3; post_contact_metres +100; tackle_busts +13; tackledOpp20 +5; complete_sets -5; errors +9; inCompleteSets +5; penalties_conceded -5; missed_tackles -13. Report context: late / sin bin |
| 17 | Canterbury-Bankstown Bulldogs vs Cronulla-Sutherland Sharks | 15-14 | stat_reversal | Cronulla-Sutherland Sharks | Canterbury-Bankstown Bulldogs | high | 20.93 | try_assists +3; run_metres +122; tackle_busts +19; tackledOpp20 -20; territory +12.9; complete_sets -9; inCompleteSets +4; penalties_conceded +4; missed_tackles -19 |
| 18 | Canterbury-Bankstown Bulldogs vs New Zealand Warriors | 13-12 | stat_reversal | New Zealand Warriors | Canterbury-Bankstown Bulldogs | high | 21.55 | post_contact_metres +157; tackle_busts +17; tackledOpp20 +13; missed_tackles -17 |
| 18 | North Queensland Cowboys vs Manly-Warringah Sea Eagles | 20-21 | stat_reversal | North Queensland Cowboys | Manly-Warringah Sea Eagles | medium | 14.76 | run_metres +242; post_contact_metres +100; tackle_busts -3; tackledOpp20 +8; territory +30.5; errors +3; missed_tackles +3 |
| 19 | Dolphins vs South Sydney Rabbitohs | 36-28 | stat_reversal | South Sydney Rabbitohs | Dolphins | low | 7.18 | run_metres -237; tackle_busts +9; tackledOpp20 -6; territory -32.8; complete_sets +7; errors -8; inCompleteSets -4; missed_tackles -9. Report context: late |
| 20 | Canberra Raiders vs New Zealand Warriors | 20-18 | stat_reversal | New Zealand Warriors | Canberra Raiders | medium | 14.84 | tackledOpp20 +9; territory +18.9; complete_sets +3; inCompleteSets -3 |
| 20 | Penrith Panthers vs Dolphins | 28-26 | close_game_tension | Dolphins | Penrith Panthers | medium | 9.51 | run_metres -290; tackle_busts -20; tackledOpp20 -9; territory -12.3; errors -7; inCompleteSets -8; penalties_conceded +3; missed_tackles +20. Report context: controversial / late |
| 21 | Parramatta Eels vs Melbourne Storm | 14-32 | margin_exaggeration | Parramatta Eels | Melbourne Storm | low | 8.96 | line_breaks -3; tackle_busts -14; tackledOpp20 +42; possession_percentage +8; territory +17.7; complete_sets +4; missed_tackles +14. Report context: controversial / injury |
| 22 | New Zealand Warriors vs Parramatta Eels | 20-30 | stat_reversal | New Zealand Warriors | Parramatta Eels | medium | 15.64 | run_metres +149; post_contact_metres +81; tackle_busts +18; tackledOpp20 +22; territory +26.1; complete_sets +6; penalties_conceded -5; missed_tackles -18 |
| 22 | Melbourne Storm vs St. George Illawarra Dragons | 16-18 | stat_reversal | Melbourne Storm | St. George Illawarra Dragons | medium | 13.78 | run_metres +206; post_contact_metres +82; tackledOpp20 +10; territory +25.2 |
| 23 | Dolphins vs New Zealand Warriors | 34-32 | close_game_tension | New Zealand Warriors | Dolphins | low | 9.26 | line_breaks -3; run_metres +135; post_contact_metres +205; tackle_busts -17; tackledOpp20 +28; territory +16.5; complete_sets +3; inCompleteSets -4; missed_tackles +17 |
| 24 | Penrith Panthers vs Melbourne Storm | 22-24 | close_game_tension | Penrith Panthers | Melbourne Storm | medium | 14.43 | tackle_busts -9; tackledOpp20 -9; errors +4; missed_tackles +9. Report context: bunker / controversial |
| 24 | Wests Tigers vs South Sydney Rabbitohs | 18-16 | stat_reversal | South Sydney Rabbitohs | Wests Tigers | high | 17.35 | line_breaks +3; run_metres +314; post_contact_metres +161; tackle_busts +21; tackledOpp20 +6; territory +10.8; errors +6; inCompleteSets +5; missed_tackles -21. Report context: injury / late |
| 25 | Canberra Raiders vs Penrith Panthers | 22-18 | stat_reversal | Penrith Panthers | Canberra Raiders | high | 21.4 | line_breaks +3; run_metres +244; tackle_busts +5; tackledOpp20 +19; possession_percentage +8; territory +34; errors +3; inCompleteSets +4; penalties_conceded -4 |
| 26 | North Queensland Cowboys vs Melbourne Storm | 38-30 | stat_reversal | Melbourne Storm | North Queensland Cowboys | high | 18.55 | run_metres +135; tackle_busts +24; tackledOpp20 +22; forced_drop_outs +4; complete_sets +3; missed_tackles -24 |
| 26 | Sydney Roosters vs Canberra Raiders | 12-14 | stat_reversal | Sydney Roosters | Canberra Raiders | high | 53.46 | line_breaks +3; run_metres +577; post_contact_metres +171; tackle_busts +31; tackledOpp20 +41; possession_percentage +22; territory +49; complete_sets +10; inCompleteSets +3. Report context: injury / late |
| 27 | St. George Illawarra Dragons vs Canberra Raiders | 24-26 | close_game_tension | St. George Illawarra Dragons | Canberra Raiders | low | 9.61 | tackledOpp20 +5; possession_percentage +6; complete_sets +3 |
| 28 | Canterbury-Bankstown Bulldogs vs Manly-Warringah Sea Eagles | 22-24 | close_game_tension | Canterbury-Bankstown Bulldogs | Manly-Warringah Sea Eagles | medium | 10.28 | tackle_busts -17; tackledOpp20 -4; forced_drop_outs +3; complete_sets +4; errors -3; inCompleteSets -5; missed_tackles +17. Report context: injury / late |

## Method

A stat dominance score is calculated from score-independent match stats: line breaks, try assists, run metres, post-contact metres, tackle busts, opposition-20 tackles, forced dropouts, possession, territory, complete sets, errors, incomplete sets, penalties conceded, missed tackles and sin bins.

A game is an adjustment candidate when the scoreboard winner is opposite to the stat dominance winner, when the margin looks inflated relative to the stat profile, or when a close result has weak winner support plus report context. Within each round, the top candidate is flagged above threshold and a second candidate is allowed when its score is also strong.

Reports are not used to create the stat score. They only add context terms such as controversial, bunker, penalty try, sin bin, injury, HIA, no try, late, intercept, against the run of play or comeback.
