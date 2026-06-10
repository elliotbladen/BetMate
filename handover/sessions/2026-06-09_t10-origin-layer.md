# Session Diary — 2026-06-09
## T10 Origin Layer + NRL CLV Analysis + H2H Lookup

---

### What was done this session

#### 1. NRL CLV Model Agreement Analysis (R10–R13)
Confirmed the Category A/B/C pattern holds for NRL as well as AFL:

- **Category A** (both models agree, bet WITH): positive CLV, correct approach
- **Category B** (both models agree, bet AGAINST): negative CLV — R13 Cowboys bet was this
- **Category C** (models disagree): mixed but generally low confidence bets

R13 had two distinct failure modes:
1. **Preventable**: Betting against both model signals (Category B)
2. **Harder to prevent**: Panthers — both models agreed but sharp money moved line 6pts against us post-bet. Timing issue, not model issue.

NRL CLV running: +2.12% (R10–R13). Still positive but needs monitoring.

---

#### 2. R12 Origin Audit
Confirmed R12 machine pricing completely missed all Origin players from T5:
- Storm: Munster (elite), Grant (elite), Loiero (rotation) — 8.5pts of Origin impact not in machine T5
- Bulldogs: Crichton (key) — 2.5pts not captured
- T5 casualty ward scraper has no visibility into Origin camp — never did

The manual overlay in `r12_round_pricing_2026.md` was applied correctly for the Fri–Sun games, and the Thu May 21 game was correctly excluded (camp started Fri May 22). But the manual process was fragile.

---

#### 3. T10 Origin Layer — LIVE

Built and deployed a permanent automated Origin adjustment tier.

**Files created:**
- `BettingEngine/pricing/tier10_origin.py` — tier logic
- `data/nrl/origin/2026.json` — G1/G2/G3 camp windows + G1 squads
- `BettingEngine/db/migrations/024_tier2_t10_origin.sql` — 7 new columns on tier2_performance

**Files modified:**
- `BettingEngine/scripts/prepare_round.py` — T10 integrated into pricing loop
- `BettingEngine/scripts/export_round_csv.py` — T10 columns in CSV output
- `BettingEngine/config/tiers.yaml` — tier10_origin config block
- `BettingEngine/db/queries.py` — insert_tier2_performance extended with T10 fields

**How it works:**
1. `_load_origin_data(season)` reads `data/nrl/origin/{season}.json`
2. `find_active_origin_game(match_date, origin_data)` detects if `camp_start <= match_date < camp_end`
3. `compute_team_origin_pts(team_name, origin_game)` sums tier weights for each team's absent players
4. `compute_origin_adjustments(h_pts, a_pts, config)` produces `handicap_delta` + `totals_delta`
5. Applied to `final_mrg` and `raw_final_total` in price_match()
6. Camp window detection correctly handles Thursday exclusion (May 21 game falls before camp_start May 22)

**Config in tiers.yaml:**
```yaml
tier10_origin:
  enabled: true
  handicap_clamp: 4.0        # wider than T5 (3.0) — more players affected
  totals_threshold: 2.5      # suppress totals if combined pts > 2.5
  totals_rate: -0.3          # pts per origin point excess
  totals_cap: -3.0           # max totals suppression
```

**Origin JSON structure** (`data/nrl/origin/2026.json`):
```json
{
  "season": 2026,
  "origin_games": [
    {
      "game_number": 1,
      "date": "2026-05-28",
      "camp_start": "2026-05-22",
      "camp_end": "2026-05-29",
      "nsw_squad": [
        {"player": "Nathan Cleary", "team": "Penrith Panthers", "tier": "elite"},
        ...
      ],
      "qld_squad": [...]
    },
    {
      "game_number": 2,
      "date": "2026-06-17",
      "camp_start": "2026-06-12",
      "camp_end": "2026-06-18",
      "nsw_squad": [],
      "qld_squad": []
    },
    {
      "game_number": 3,
      "date": "2026-07-08",
      "camp_start": "2026-07-03",
      "camp_end": "2026-07-09",
      "nsw_squad": [],
      "qld_squad": []
    }
  ]
}
```

**G1 squads (fully populated):**

NSW: Cleary (Panthers, elite), Crichton (Bulldogs, key), Koula (Manly, rotation), Olakau'atu (Manly, key), Barnett (Warriors, rotation), Murray (Rabbitohs, key)

QLD: Munster (Storm, elite), Grant (Storm, elite), Loiero (Storm, rotation), Fifita (Titans, key), Fa'asuamaleaui (Titans, key), Cotter (Cowboys, key), Capewell (Warriors, key)

**ACTION REQUIRED before R15 (Origin G2 week):**
Update `data/nrl/origin/2026.json` G2 nsw_squad and qld_squad arrays with announced squad.
Camp window is already set: camp_start 2026-06-12, camp_end 2026-06-18.
Games in that window (R15 Thu–Sat): any game on Jun 12+ is affected.

**ACTION REQUIRED before R18 (Origin G3 week):**
Update G3 nsw_squad and qld_squad. Camp: Jul 3–9.

---

#### 4. Betting Edge Math
Clarified the EV formula for the user:
- `EV = (market_odds / model_fair) - 1`
- Market odds already embed overround — do NOT subtract it separately
- A 15% model edge = 15% EV (not 10%)
- 15% is a defensible conservative threshold: ~5–8% model uncertainty buffer + ~2–3% line movement risk

---

#### 5. Gold Coast Suns vs Geelong — Last 5 H2H (2022+)

Database only has records from 2022, so 5 games retrieved (they haven't played 6 times since then):

| Date | Result | Margin | Venue |
|------|--------|--------|-------|
| 2026-03-06 | Gold Coast 125 def Geelong 69 | 56 pts | People First Stadium |
| 2025-06-07 | Geelong 61 def Gold Coast 37 | 24 pts | GMHBA Stadium |
| 2024-05-16 | Gold Coast 164 def Geelong 100 | 64 pts | TIO Stadium |
| 2023-04-02 | Gold Coast 73 def Geelong 54 | 19 pts | People First Stadium |
| 2022-08-13 | Geelong 119 def Gold Coast 59 | 60 pts | People First Stadium |

Gold Coast leads 3-2 in this period. Gold Coast is 3-1 at home (People First / Darwin). Geelong's home win was 24 pts in Geelong. Margins are consistently large in both directions.

---

### Pending / Carry-forward
- G2 origin squads (Jun 12 camp) — populate before R15 pricing
- G3 origin squads (Jul 3 camp) — populate before R18 pricing
- R14 CLV: NRL + AFL closing lines still outstanding
- Custom domain betmate.au: www CNAME fix
- Refs on Vercel: wire to Supabase key
- Supabase UNIQUE constraint: `ALTER TABLE betmate_data_store ADD CONSTRAINT betmate_data_store_key_unique UNIQUE (key);`
