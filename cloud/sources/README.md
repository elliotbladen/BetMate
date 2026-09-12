# Team sheet and availability sources — what was tested, and what survived

Every claim below was verified by HTTP request on 2026-09-13, not taken from
documentation or a search result. This repo has been burned twice by sources that
return `200 OK` with no usable payload (efl.com's Nuxt shell, Understat's empty
league pages), so "it responds" is not evidence — **the test is whether real player
names come back**.

## Chosen sources

| Code | Source | Gives | Verified |
|---|---|---|---|
| EPL, EFL Championship, UCL | **FotMob** `api/data/matchDetails` | predicted + confirmed XI, unavailable players, injury reason, expected return | ✅ |
| NFL | **NFL.com** `/injuries/` | the league-mandated practice report | ✅ |

## Why FotMob for all three football codes

One endpoint answers both halves of the job. From a single `matchDetails` call:

```
content.lineup.lineupType         confirmed | predicted | lastStarting11
content.lineup.homeTeam.formation e.g. "3-4-3"
content.lineup.homeTeam.starters  11 players, with id / name / shirtNumber / position
content.lineup.homeTeam.unavailable
    -> name, unavailability.type ("injury"), unavailability.expectedReturn
```

Real output captured from Coventry v Brighton, 13 Sep:

```
Kaine Kesler-Hayden   injury   return=Mid October 2026
Haji Wright           injury   return=Early November 2026
Georginio Rutter      injury   return=Doubtful
```

**`lineupType` is the confidence marker and must be stored.** It degrades with
distance from kickoff, measured:

| Lead time | lineupType | XI | unavailable |
|---|---|---|---|
| same day | `predicted` | 11 | 4 |
| +1 day | `predicted` | 11 | 3 |
| +2 days | `lastStarting11` | 11 | 1 |

So the **XI** is only meaningful from about T-1; the **unavailable list** is
populated further out and is the part that matters 1-3 days ahead. A consumer that
treats `lastStarting11` as a real prediction is reading last week's team.

FotMob is also already the only proven route for referee appointments in this repo
(`CLAUDE.md`), so this consolidates rather than adds a dependency. Coverage
confirmed for Premier League and Championship (`ccode` `ENG`) and Champions League
(`ccode` `INT`, 9 matches per matchday, checked against 13-14 Oct).

Underlying data is credited to `enetpulse`.

## Why NFL.com for the NFL

The NFL is the one code here with a **league-mandated** injury report: clubs must
file practice participation on each practice day and a game-status designation
before the game. That makes the official page a primary source rather than an
aggregator — nobody else knows better, they are all reporting this.

Verified server-rendered (366 KB of HTML, no JS required):

```
Full Participation      96
Limited Participation   50
Did Not Participate     36
Questionable            24
Doubtful                 6
```

There is **no** `__NEXT_DATA__` blob, so this needs HTML parsing rather than a JSON
lift. That is the trade for using the authoritative source.

## Rejected, with reasons

| Source | Result |
|---|---|
| premierleague.com/latest-player-injuries | 200, 84 KB, **zero** injury words — client-rendered shell |
| skysports.com injury tracker | 200, 255 KB, **zero** injury words — loaded by JS |
| premierinjuries.com | **403** to a plain client |
| physioroom.com | **404** |
| ESPN `site.api.espn.com` | **403 on every endpoint** — see below |

## ⚠️ ESPN is rate-limiting this machine

Every ESPN endpoint returned 403 during this research, including
`soccer/eng.1/scoreboard`, which this repo uses successfully. Cached ESPN match
feeds on disk are timestamped **the same morning**, so ESPN was working hours
earlier — this is a throttle, not a permanent change.

`com.bettingengine.championship-player-snapshots` is an existing scheduled ESPN
consumer. **Any new collector must not add uncoordinated ESPN load**, which is a
second reason the football codes route through FotMob instead.

## Rules for adding a source here

1. Prove it returns real player names before writing a parser against it.
2. Record `lineup_type` / designation verbatim — never flatten a prediction and a
   confirmation into the same field.
3. Throttle, and cache raw payloads, so a re-parse never costs a second fetch.
