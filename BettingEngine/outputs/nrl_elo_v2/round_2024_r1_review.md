# NRL Elo v2 Review - 2024 Round 1

Purpose: first manual label pass for the Elo v2 "hard done by / lucky winner" signal. Scoreboard and stats drive the label; reports are used only as confirmation or context.

## Labels

| Match | Result | Label | Elo v2 action |
| --- | ---: | --- | --- |
| Sea Eagles vs Rabbitohs | Manly 36-24 | Normal | Full result update |
| Roosters vs Broncos | Roosters 20-10 | Normal | Full result update |
| Knights vs Raiders | Raiders 28-12 | Normal | Full result update |
| Warriors vs Sharks | Sharks 16-12 | Warriors hard done by / Sharks lucky winner | Reduce winner reward and loser penalty |
| Storm vs Panthers | Storm 8-0 | Panthers hard done by / Storm lucky winner | Reduce winner reward and loser penalty |
| Eels vs Bulldogs | Eels 26-8 | Normal | Full result update |
| Titans vs Dragons | Dragons 28-4 | Normal | Full result update |
| Dolphins vs Cowboys | Cowboys 43-18 | Normal | Full result update |

## Main Flags

### Warriors 12, Sharks 16

This is the cleanest Round 1 mismatch. Warriors lost by 4 but had the better underlying profile almost everywhere except final conversion.

- Run metres: Warriors +360
- Post-contact metres: Warriors +106
- Tackle busts: Warriors +10
- Tackles in opposition 20: Warriors +28
- Forced dropouts: Warriors +5
- Possession: Warriors +8 percentage points
- Territory: Warriors +32.7 percentage points
- Complete sets: Warriors +8
- Missed tackles: Warriors -10

Elo v2 treatment: do not give Cronulla a full winner boost. Protect Warriors from the full loser penalty.

### Storm 8, Panthers 0

Penrith were held scoreless, so this should not be reversed into a Penrith "deserved win". But the field-position and pressure stats say the 8-0 result was not a normal clean Storm superiority signal.

- Territory: Panthers +38.1 percentage points
- Tackles in opposition 20: Panthers +25
- Forced dropouts: Panthers +4
- Complete sets: Panthers +6
- Run metres: Panthers +140
- Tackle busts: Panthers +13
- Line breaks: Panthers +1

Elo v2 treatment: give Melbourne credit for defence and finishing, but reduce the Elo swing. Penrith should not be punished like a normal away shutout loser.

## Non-Flags

- Cowboys-Dolphins had a report note about a controversial penalty try, but the Cowboys won the stat sheet strongly and by 25. No luck tag.
- Titans had lots of opposition-20 tackles against the Dragons but generated zero line breaks and were beaten badly across tackle busts, run metres and missed tackles. No hard-done-by tag.
- Souths goal kicking was poor against Manly, but Manly had enough territory, metre and discipline edge to keep the result as normal.

## Proposed Round 1 Training Signal

For the two high-confidence mismatch games:

```text
luck_multiplier = 0.50
```

That means if standard Elo would move winner +10 and loser -10, Elo v2 would move winner +5 and loser -5.

Do not reverse the result yet. Reversal should be a later aggressive experiment only if conservative dampening improves 2025 backtest accuracy.
