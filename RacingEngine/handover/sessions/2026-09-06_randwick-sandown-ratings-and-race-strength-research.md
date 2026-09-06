# Randwick/Sandown 5 Sep ratings + Race Strength Engine research

Date: 6 September 2026

## 1. Imported Randwick + Sandown (5 Sep 2026) into the canonical DB

No FormFav key on this machine, so a one-off converter was used
(`store.upsert_result` / `upsert_sectionals` / `upsert_race_classification`):

- **Randwick** (`racing-com-nsw-authorised-v2`): results from the Racing.com
  card, sectionals from the ATC Swiss Timing PDF (published ~24 h after racing).
- **Sandown** (`racing-com-rv-authorised`): results + sectionals from the
  Racing.com card. R9/R10 sectionals still unpublished at import.
- Margins parsed from the "1.16L" strings, cross-checked against ATC finish-time
  gaps for Randwick R1 and R8 only.
- DB backed up first: `data/racing_engine.sqlite.bak-0905` (1.7 GB — safe to
  delete, or keep as rollback). Re-import via the standard FormFav path when a
  key is available to supersede these rows.
- Raw source archived under `data/raw/rnsw/2026-09-05/` and
  `data/raw/racing-com/2026-09-05/`.

## 2. `form-first-v2.0` rebuild (`--as-of 2026-09-06`)

Ran clean in ~11 s: 20/20 races kept, 186 run performances, 2 minor clock
quarantines. **Sanity gate PASSED** — audit Spearman **0.686** vs 24 published
2024/25 official ratings.

Best runs of the day:

| Run | Rating | Race |
|---|---:|---|
| Lindermann (won) | **117.5** | Randwick R9, Chelmsford Stakes, G2 1600m |
| Ceolwulf (2nd) | 113.8 | Randwick R9 |
| Tempted (won) | 110.7 | Randwick R8, Concorde Stakes, G2 1000m |
| Headwall (2nd) | 110.6 | Randwick R8 |
| Headley Grange (won) | 110.1 | Randwick R7, G2 1400m |
| My Gladiola (won) | 108.1 | Sandown R8, **Moir Stakes, G1** 1000m |

Randwick R9 (Chelmsford) was the strongest race of the day — a 119-rated horse
ran 2nd.

## 3. The Moir vs Concorde finding (important — user asked to verify)

The Moir (G1) rated **below** the Concorde (G2): race strength 108.1 vs 110.7.
This is a genuine class read, **not** a track penalty:

- `form-first-v2.0` has **zero going/track input** (`clock_used_for_level:
  false`). Soft ground cannot lower the figure — no mechanism.
- The only indirect track effect (Soft spreading beaten margins) is neutralised:
  the collateral anchors are the top-4 finishers, all beaten ≤ 1.25 L; the
  strung-out tail (Giga Kick 10th, Rothfire 8th) is deliberately excluded.
- The Moir field's own official ratings topped at Giga Kick 116, most 100–112;
  the class horses all ran below form in a false-tempo race (early score −2.87);
  My Gladiola (79→90→106→108) and Cavalry Girl (59→83→96→96) beat each other by
  0.35 L.
- The model produces proper G1 figures when fields are strong — Beiwacht 120.4,
  Autumn Glow 119.7 in the past fortnight.
- The "45 % of G1 winners rate < 110" scare is explained: most are 2yo Group 1s
  (Golden Slipper etc.), rated on a scale calibrated to open company.

Residual soft spots: Natural Fling carried 50 kg (field otherwise 56.5–58.5) —
likely genuine young-WFA relief, ≤ 1.5 pt impact on the winner; import
margin-verified on only 2 of 20 races; V2.10 shadow not run for these meetings.

## 4. Race Strength Engine — architecture drafted

`docs/race_strength_engine_architecture.md` — proposed `race-strength-shadow-v1`.

Purpose: quantify the quality of opposition a horse has been racing against, so
that when Moir horses meet Concorde horses the engine favours the Concorde
form. Target 1–5 % of the pricing signal, shadow-only under promotion gates.

Four layers, all buildable from the existing DB (no new feed):

1. **Race Strength Index** — revise `v2_run_performances.race_strength` with a
   grade prior, tempo-integrity down-weighting of the beaten tail, and a bounded
   time-vs-par cross-check.
2. **Franked RSI** — append-only, time-stamped; revise a race's strength as its
   participants run again. Generalises the one-pair hack in
   `collateral_revision_v2.py`. Highest-value layer.
3. **Class Exposure** — per horse: `class_ceiling`, decayed `class_habitual`,
   confidence.
4. **Matchup Class Delta** — bounded (±2 pt to start), zero-centred per field
   adjustment for an upcoming race, plus a race-level `class_spread` signal.

Deep option (v2, not scheduled): simultaneous solve for horse ability and race
strength via Whole-History Rating / Massey / Plackett–Luce.

Resume point: build `racing_engine/race_strength_index.py` (Layer 1).

## 5. Also this session (BettingEngine, separate)

Championship 1X2 calibration investigation + T5 injury guardrails — committed
`8e852f7`. See `BettingEngine/handover/sessions/2026-09-06_championship-1x2-calibration-t5-cap.md`.
