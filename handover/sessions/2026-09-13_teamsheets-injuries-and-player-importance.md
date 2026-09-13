# 2026-09-13 — Team sheets, injury sources, and a player importance rating

**Branch:** `feat/teamsheets-and-injuries`, 10 commits, not merged. Nothing in this
session touches the live collectors or the site.

---

# PART 1 — Team sheet and injury sources (architecture, verified)

Every source claim was proven by HTTP request, not taken from documentation. This
repo has twice been burned by sources that return `200 OK` with no usable payload,
so the test is **whether real player names come back**.

| Code | Source | Gives |
|---|---|---|
| EPL / EFL / UCL | **FotMob** `api/data/matchDetails` | predicted + confirmed XI, unavailable list, injury reason, expected return |
| NFL | **nflverse** (GitHub release CSVs) | snap counts, depth charts, the mandated injury report |

## FotMob answers both halves from one call

```
content.lineup.lineupType              confirmed | predicted | lastStarting11 | standard
content.lineup.homeTeam.starters       11 players
content.lineup.homeTeam.unavailable    name, unavailability.type, expectedReturn
```

Real capture: `Kaine Kesler-Hayden, injury, return=Mid October 2026`.

⚠️ **`lineupType` is the confidence marker and MUST be stored.** Measured ladder:

| lead time | lineupType | meaning |
|---|---|---|
| +2 days | `lastStarting11` | **last week's team — NOT a forecast** |
| +1 day | `predicted` | a real predicted XI |
| in-play | `standard` | the actual XI |

**The XI is only meaningful from ~T-1; the UNAVAILABLE list is populated further out
and is the real 1-3 day signal.** Anything flattening these four into one field is
reading fiction.

## nflverse is better than what football has

`snap_counts` (offense/defense/st pct per game), `depth_charts` (**`pos_rank`** —
starter vs backup, stated not inferred), `injuries` (report + practice status, the
mandated report already structured). Multi-season. **This replaced the nfl.com HTML
scraper written earlier the same day.**

## Rejected, each tested

premierleague.com (200, 84KB, **zero** injury words — JS shell), skysports.com
(200, 255KB, zero), premierinjuries.com (403), physioroom (404),
pro-football-reference (403), nfl.com depth charts (404).

⚠️ **ESPN 403s EVERY endpoint from this machine**, including one this repo uses
successfully. Cached feeds on disk were timestamped the same morning, so it is a
throttle, not a change. `com.bettingengine.championship-player-snapshots` is an
existing scheduled ESPN consumer — a second reason football routes via FotMob.

## Written, not yet applied

`supabase/migrations/20260913_team_sheets_and_availability.sql` — a change-log, not
a snapshot store, because the value is **when** news broke. Same shape as
`odds_quote_changes`. RLS on; unique constraints documented as the `on_conflict`
targets (both lessons from 12 Sep).

---

# PART 2 — Player importance rating

## NFL: DONE, all 32 teams, 3,590 players

`cloud/nfl_importance.py` → `data/player_importance/nfl_importance_2026-09-13.json`

Scored as **expected points of spread movement if the player is OUT**, on the
owner's thresholds (>=3.0 → 3 star, 0.2-3.0 → 2, <0.2 → 1).

**Result: 24 star, 921 important, 2,645 not. Every tier 3 in the league is a
quarterback, and 8 starting QBs do NOT reach it** — which is the owner's "only a
very good quarterback" holding exactly.

```
Maye 5.80  Allen 5.68  Purdy 5.60  Love 5.57  Lamar 5.42  Mahomes 5.28
Cousins 2.82  Tua 2.57  Young 2.25  Rodgers 2.05  Geno 2.00  Ward 2.00
```

Highest non-QBs in the league: Hutchinson 1.20, Jalen Carter 1.20, Myles Garrett
1.19 — the three best edge rushers, found without being told who they are.

⚠️ **`points_if_out` is the column the shadow model should consume, NOT the tier.**
Purdy out (5.60) and a starting guard out (0.45) are different events.

## Football: METHOD PROVEN on 3 clubs, NOT rolled out

`cloud/football_star_rating.py` → `data/player_importance/football_stars_2026-09-13.json`

Binary: **2 = a Van Dijk / Rodri / Mbappé, 1 = everyone else.** A 2 must clear BOTH
gates — every failed approach used only one:

* **first choice** — 70+ min per appearance across >=30% of matches
* **elite** — rating >= 85th percentile of his position group **league-wide**

Premier League bars: keepers 7.48, defenders 7.23, midfielders 7.49, attackers 7.31.

| club | 2-stars |
|---|---|
| Liverpool | Gakpo, Szoboszlai, **Van Dijk**, Wirtz |
| Chelsea | Cole Palmer, João Pedro |
| Real Madrid | Mbappé, Bellingham, Vinícius Jr, Valverde |

**Owner signed off on this output.** Both gates demonstrably do separate work:
Morgan Rogers has Chelsea's highest rating (8.04) and is a **1** — 4 games played.
Alisson plays 90 min every time picked and is a **1** — 6.85 against a 7.48 keeper
bar. Arda Güler rates 8.09 but averages 58 min, so **1**.

⚠️ **The 85th percentile is a JUDGEMENT about scarcity, not a derived fact.** It is
the single knob controlling how rare a 2 is. p90 would likely cut Wirtz and
Szoboszlai; p80 would add Mac Allister and Gravenberch.

---

# ⚠️ THREE APPROACHES TESTED AND REJECTED — do not re-litigate

**1. MARKET VALUE — disqualified.** Measures resale price and collapses with age:
**Van Dijk €5m, Alisson €12m** while both play every available minute. It rated the
owner's two canonical stars "not important". It also gave Liverpool ZERO stars (an
evenly expensive squad flattens share-of-squad) while giving City one, purely
because Haaland is an outlier in his own squad.

**2. AVAILABILITY-WEIGHTED ROLE — disqualified.** An early NFL version scored
`(games_played / team_games) x snap_pct`, so **Nick Bosa (4 of 18, injured) and Fred
Warner (7 of 18) scored low**. A model for pricing injuries penalising players for
having been injured. Role and availability are now separate fields everywhere.

**3. WITH-OR-WITHOUT-YOU — the right idea, fatally blocked.** `cloud/wowy.py` and
`cloud/wowy_pooled.py` work and are committed; the data is real. But:

* Over **THREE pooled seasons** Van Dijk still missed too few matches to measure.
* The top of every list is a **backup goalkeeper** who played the games the first
  choice missed and happened to win them: Kelleher +0.51 (Liverpool), Petrovic +0.43
  (Chelsea), Nacho and Joselu (Real Madrid).
* Cole Palmer came out **+0.09** — indistinguishable from noise.
* Rodri surfaced (**2.60 PPG with, 1.76 without**) ONLY because an ACL cost him 33
  matches. Rúben Dias +0.84 likewise.

**The mechanism that defeats it: the best players never miss games.** WOWY measures
rotation players well and the spine not at all — the opposite of what is needed.
Keep it as CONFIRMATION where a real sample exists; never as the ranker.

---

# Open

1. **Roll the football rating out beyond 3 clubs** — EPL 20 + EFL 24 + UCL 36. Cost
   is ~30 playerData calls per club, so ~2,400 calls, roughly 45 minutes. The method
   is signed off; this is execution.
2. **Wire the collector.** The source adapters and schema exist; nothing fetches on a
   schedule yet. Cadence still undecided — suggest T-3/-2/-1 days for injuries plus
   T-2h and T-1h for the confirmed XI.
3. **Apply the migration** (needs the Supabase SQL editor).
4. **Stamp the rating onto captured injuries** — the point of the whole exercise. A
   rating is stamped `rated_on` and NEVER rewritten: a player who breaks out in
   March must not retroactively become a star in an October injury being measured.
5. **NFL: "Mike Evans" appears on the SF depth chart with 1 game.** He is a
   Buccaneer. Likely a stale nflverse row — check how common that is before trusting
   team attribution wholesale.
6. Opponent-adjust WOWY if it is ever used quantitatively.

# Not done, and not started

Championship and UCL squads. The collector. Any scheduling. Nothing from this
session runs automatically.
