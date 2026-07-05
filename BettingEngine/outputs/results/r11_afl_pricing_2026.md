# AFL Round 11 — 2026 Pricing & Results Tracker
*Sir Doug Nicholls Round 2*

**Priced:** 2026-05-21  
**Model version:** T1–T4 Rules + T1–T7 ML Shadow  
**Note:** All prices are FAIR (no bookmaker margin applied). Add ~5% to find market equivalent.

---

## Machine Engine — Full Output

### Rules Model (T1–T4)
| Game | Home H2H | Away H2H | Hdcp Line | Fair Total |
|------|----------|----------|-----------|-----------|
| Hawks vs Crows | **1.29** | 4.48 | Hawks -27.4 | 180.0 |
| Tigers vs Bombers | 2.94 | **1.52** | Bombers -14.8 | 151.0 |
| Dockers vs Saints | **1.10** | 10.58 | Dockers -47.3 | 181.5 |
| Kangaroos vs Suns | 3.33 | **1.43** | Suns -18.9 | 183.0 |
| Cats vs Swans | **1.77** | 2.29 | Cats -5.8 | 209.0 |
| Magpies vs Eagles | **1.01** | 105.26 | Magpies -84.4 | 184.5 |
| Power vs Blues | **1.26** | 4.81 | Power -29.3 | 166.0 |
| Giants vs Lions | 3.74 | **1.37** | Lions -22.3 | 191.5 |
| Bulldogs vs Demons | **1.28** | 4.54 | Bulldogs -27.7 | 181.5 |

### ML Shadow Mode (T1–T7, XGBoost bias-corrected)
| Game | Rules Margin | ML Margin | Gap | Rules Total | ML Total | Total Gap | Flag |
|------|-------------|-----------|-----|-------------|----------|-----------|------|
| Hawks vs Crows | +27.4 | +0.4 | **-27.0** | 179.9 | 169.7 | -10.2 | ◆◆◆ margin+H2H+total |
| Tigers vs Bombers | -14.8 | -13.1 | +1.7 | 150.8 | 170.8 | **+20.0** | ◆ H2H+total |
| Dockers vs Saints | +47.3 | +18.1 | **-29.2** | 181.6 | 171.3 | -10.3 | ◆◆ margin+total |
| Kangaroos vs Suns | -18.9 | -3.6 | **+15.3** | 183.2 | 151.9 | **-31.3** | ◆◆◆ margin+H2H+total |
| Cats vs Swans | +5.8 | +3.5 | -2.3 | 209.2 | 157.9 | **-51.3** | ◆◆◆ total |
| Magpies vs Eagles | +84.4 | +45.2 | -39.2 | 184.4 | 180.8 | -3.6 | ◆ margin |
| Power vs Blues | +29.3 | +23.8 | -5.5 | 166.2 | 174.6 | +8.4 | ◆ total |
| Giants vs Lions | -22.3 | -3.6 | **+18.7** | 191.4 | 182.9 | -8.5 | ◆◆◆ margin+H2H+total |
| Bulldogs vs Demons | +27.7 | +2.7 | **-25.0** | 181.5 | 165.2 | -16.3 | ◆◆ margin+total |

*◆ = divergence flag (margin ≥6pt OR H2H ≥8% OR total ≥8pt). ML is independent cross-check only — not used in pricing.*

---

## GAME 1 — Hawthorn Hawks vs Adelaide Crows
**Thu 21 May | MCG, Melbourne**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Hawks **1.29** / Crows 4.48 | Hawks ~69% (ML) |
| Handicap | Hawks **-27.4** | ML margin **+0.4** ← |
| Total | **180.0** | ML: 169.7 |

⚠️ **MAJOR ML DIVERGENCE: Rules says Hawks -27.4, ML says effectively level (+0.4)**. Gap of 27pts. Rules is almost certainly overcooking Hawks' ELO advantage here — ML has seen this matchup context before and disagrees strongly. H2H, margin AND total all flag.

**Injuries (T5 — already in model):**
- Hawks: Will Day (shoulder, out 2-3 weeks) — only listed player
- Crows: Mark Keane (calf, out), Taylor Walker (hamstring, out 2-3 weeks) — Walker a key forward

**Web update:** Cameron Nairn debuts for Hawks. Chol, Gunston, Nash all expected back fit.

**Signal:** If market has Hawks at -20 to -25, ML divergence is a strong fade signal on Hawks. **Lean Crows / Crows cover.**

| Result | Home (Hawks) | Away (Crows) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 180.0 | Hawks -27.4 |
| ML pred | — | — | 169.7 | Level (+0.4 Hawks) |
| Error | | | | |

---

## GAME 2 — Richmond Tigers vs Essendon Bombers
**Fri 22 May (Dreamtime at the G) | MCG, Melbourne**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Tigers 2.94 / Bombers **1.52** | Bombers (ML aligns) |
| Handicap | Bombers **-14.8** | ML margin **-13.1** ← close |
| Total | **151.0** | ML: 170.8 (+20.0) |

Rules and ML agree on direction (Bombers favoured, margin roughly aligned). **Total divergence: ML sees 20pts MORE scoring.** Rules may be undercooked on totals for this fixture.

**Injuries (T5 — in model):**
- Bombers: Angus Clarke (foot), Fiorini (back), Isaac Kako (back), Jordan Ridley (calf 3 wks), Lewis Hayes (knee 3 wks), Nicholas Martin (knee, season), Rhys Unwin (hamstring 6-8 wks), Saad El-Hawli (shoulder 4 wks) — heavy casualty list
- Tigers: No injuries listed in scraper

**Note:** Dreamtime at the G — historically high-intensity, emotion-charged fixture. Essendon playing away but this game has its own context.

**Signal:** Rules and ML agree on Bombers. Total: if market is sub-155, lean overs (ML sees 170+).

| Result | Home (Tigers) | Away (Bombers) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 151.0 | Bombers -14.8 |
| ML pred | — | — | 170.8 | Bombers -13.1 |
| Error | | | | |

---

## GAME 3 — Fremantle Dockers vs St Kilda Saints
**Fri 22 May | Optus Stadium, Perth**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Dockers **1.10** / Saints 10.58 | Dockers (ML aligns) |
| Handicap | Dockers **-47.3** | ML margin **-18.1** ← |
| Total | **181.5** | ML: 171.3 |

⚠️ **Rules overcooking Dockers by ~29pts on margin.** ML still has Dockers as comfortable winners (-18.1) but rules is extreme. Likely Dockers fortress + Saints travel effects stacking too hard in rules.

**Injuries (T5 — in model):**
- Dockers: **Sean Darcy** (calf, out 2-4 weeks) ⚠️ — Darcy is their #1 ruck, significant. Also: Jaeger O'Meara (HIA, out), Sam Sturt (knee 7-8 wks)
- Saints: No injuries listed

**Note:** Sean Darcy out is the big flag. Rules model may not fully weight a #1 ruck absence. Dockers handicap at -40+ is hard to cover without their best ruckman.

**Signal:** Fade rules handicap line. Market likely has Dockers -25 to -35 — still value with Saints? ML at -18 suggests Saints within 25 is likely.

| Result | Home (Dockers) | Away (Saints) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 181.5 | Dockers -47.3 |
| ML pred | — | — | 171.3 | Dockers -18.1 |
| Error | | | | |

---

## GAME 4 — North Melbourne Kangaroos vs Gold Coast Suns
**Sat 23 May | Marvel Stadium, Melbourne**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Kangaroos 3.33 / Suns **1.43** | Kangaroos **~52%** (ML) |
| Handicap | Suns **-18.9** | ML margin **-3.6** (Suns) ← |
| Total | **183.0** | ML: 151.9 (-31.3) |

⚠️ **TRIPLE DIVERGENCE — All three metrics flag.** ML sees this as essentially a coin flip (52.3% Roos vs 30% rules). Rules has Suns -18.9, ML barely -3.6. AND total divergence of 31 pts.

**Injuries (T5 — in model):**
- Kangaroos: Blake Thredgold (foot), Jackson Archer (knee, season), River Stevens (knee 6 wks), Robert Hansen (groin), Zac Fisher (hamstring 2-3 wks)
- Suns: Elliott Himmelberg (knee 4-6 wks), Jy Farrar (ankle 6+ wks), Sam Clohesy (suspended — back R11, available)

**Web update:** North Melbourne without Powell (VFL setback).

**Signal:** If market has Suns -15 to -18, ML says that's too wide — **Kangaroos cover or upset a real possibility.** Total: strong unders lean (ML 151 vs rules 183).

| Result | Home (Kangaroos) | Away (Suns) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 183.0 | Suns -18.9 |
| ML pred | — | — | 151.9 | Suns -3.6 |
| Error | | | | |

---

## GAME 5 — Geelong Cats vs Sydney Swans
**Sat 23 May | GMHBA Stadium, Geelong**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Cats **1.77** / Swans 2.29 | Cats ~56% (close, ML aligns) |
| Handicap | Cats **-5.8** | ML margin **-3.5** ← close |
| Total | **209.0** | ML: 157.9 (**-51.3**) |

Both models agree on direction and margin (Cats slight home favourites, ~5-6pt win). **TOTAL DIVERGENCE IS MASSIVE — 51 POINTS.** Rules says 209, ML says 158. Rules is almost certainly broken on this total.

**Injuries (T5 — in model):**
- Cats: Harley Barker (knee, indefinite), Jay Polkinghorne (foot 3-5 wks), Keighton Matofai-Forbes (foot 4 wks), Toby Conway (foot, TBC), Tyson Stengle (out, individualised program)
- Swans: Matt Roberts (groin, out 2+ weeks), Corey Warner fit and in form

*Web update:* "Game of the year" billing. Both teams near top of ladder.

**Signal: STRONG UNDERS on total.** If market line is 155–175, rules 209 is the outlier — ML at 158 aligns with market range. Fade rules entirely on total here. H2H: Cats slight home favourites, both models agree — no edge.

| Result | Home (Cats) | Away (Swans) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 209.0 | Cats -5.8 |
| ML pred | — | — | 157.9 | Cats -3.5 |
| Error | | | | |

---

## GAME 6 — Collingwood Magpies vs West Coast Eagles
**Sat 23 May | MCG, Melbourne**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Magpies **1.01** / Eagles 105.26 | Magpies ~95% (ML) |
| Handicap | Magpies **-84.4** | ML margin **-45.2** ← |
| Total | **184.5** | ML: 180.8 (close) |

Magpies win regardless. Rules -84.4 is an extreme line — Eagles are the worst team in the comp but -84 is excessive. ML at -45 is more realistic. **Only margin flag fires** (total and H2H both agree).

**Injuries (T5 — in model):**
- Magpies: Harry Perryman (hamstring 4-5 wks), Joel Cochran (shoulder 4-6 wks), Reef McInnes (knee, season), Tim Membrey (hamstring 2-3 wks)
- Eagles: No injuries listed in scraper (most players average quality, deep in losses)

**Signal:** Avoid -84 line. If market has Magpies -40 to -55, that's closer to ML reality. No H2H or total value.

| Result | Home (Magpies) | Away (Eagles) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 184.5 | Magpies -84.4 |
| ML pred | — | — | 180.8 | Magpies -45.2 |
| Error | | | | |

---

## GAME 7 — Port Adelaide Power vs Carlton Blues
**Sat 23 May | Adelaide Oval, Adelaide**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Power **1.26** / Blues 4.81 | Power ~73% (ML aligns) |
| Handicap | Power **-29.3** | ML margin **-23.8** ← |
| Total | **166.0** | ML: 174.6 (+8.4) |

Both models agree on direction (Power at home). Margin gap moderate (-5.5 pts). Small total divergence (ML slightly higher). No extreme flags.

**Injuries (T5 — in model):**
- Power: Connor Rozee (hamstring, out 8-10 wks) ⚠️ — Rozee is one of Port's best players. Jack Lukosius (groin 3-5 wks), Josh Sinn (shoulder 12-14 wks)
- Blues: Harry O'Farrell (knee), Jesse Motlop (knee, season), Lucas Camporeale (kidney), Rob Monahan (shoulder, season)

**Key manual flag — Connor Rozee:** Out 8-10 weeks. He is Power's engine, averaging 25+ disposals. His absence is significant and may not be fully weighted in T5 (all players classified "average" in scraper). Power handicap may be vulnerable without him.

**Signal:** Power still win but Rozee absence narrows the margin. If market has Power -25 to -30, worth checking — ML at -23.8 without fully accounting for Rozee. **Lean Blues cover or treat as low-confidence Power.**

| Result | Home (Power) | Away (Blues) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 166.0 | Power -29.3 |
| ML pred | — | — | 174.6 | Power -23.8 |
| Error | | | | |

---

## GAME 8 — Greater Western Sydney Giants vs Brisbane Lions
**Sun 24 May | ENGIE Stadium, Sydney**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Giants 3.74 / Lions **1.37** | Giants **~49%** (ML) |
| Handicap | Lions **-22.3** | ML margin **-3.6** (Lions) ← |
| Total | **191.5** | ML: 182.9 (-8.5) |

⚠️ **TRIPLE DIVERGENCE — All three metrics flag.** Rules says Lions -22.3, ML says Lions barely -3.6 (effectively a coin flip). H2H: rules 26.7% Giants, ML 48.9%. Gap of 18.7 pts on margin.

**Injuries (T5 — in model):**
- GWS: Cody Angove (hamstring), Darcy Jones (knee), Joshua Kelly (hip, TBC) ⚠️, Logan Smith (knee), Nathan Wardius (knee), Nick Madden (knee 6-8 wks), Sam Taylor (hamstring 3 wks), Tom Green (knee, SEASON) ⚠️
- Lions: Daniel Annable (shoulder), Eric Hipwood (knee 5-6 wks), Henry Smith (foot 8 wks), Jack Payne (knee), Oscar Allen (foot 10-14 wks)

**Note:** GWS missing Joshua Kelly + Tom Green (both key midfielders). Heavy injury toll. BUT ML still sees them as near-50/50 with Lions — Lions have their own significant absentees.
**Web update:** Dayne Zorko (managed R10) expected back for Lions.

**Signal:** Rules -22.3 looks too wide. ML at -3.6 says this is a genuine contest. **GWS at home, cover or upset a real possibility.** If market has Lions -15 to -20, lean Giants cover.

| Result | Home (Giants) | Away (Lions) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 191.5 | Lions -22.3 |
| ML pred | — | — | 182.9 | Lions -3.6 |
| Error | | | | |

---

## GAME 9 — Western Bulldogs vs Melbourne Demons
**Sun 24 May | Marvel Stadium, Melbourne**

| | Rules (fair) | ML shadow |
|---|---|---|
| H2H | Bulldogs **1.28** / Demons 4.54 | Bulldogs ~75% (ML aligns on direction) |
| Handicap | Bulldogs **-27.7** | ML margin **-2.7** ← |
| Total | **181.5** | ML: 165.2 (-16.3) |

Rules says Bulldogs -27.7, ML says only -2.7. **Gap of 25pts.** Similar to Hawks vs Crows — rules overcooking the home side.

**Injuries (T5 — in model):**
- Bulldogs: Tim English (HIA/concussion, still out per web update) ⚠️ — #1 ruck, major loss
- Demons: Brody Mihocek (hamstring 3-5 wks), Christian Salem (foot 2-3 wks), Jack Viney (calf, TBC) ⚠️, Jai Culley (knee, season), Ricky Mentha (ankle), Shane McAdam (calf), Tom Campbell (neck), Xavier Lindsay (groin 2-4 wks)

**Key manual flag — Tim English:** Still in HIA protocols. Bulldogs' #1 ruck. His absence significantly undermines their engine room. Machine T5 may undervalue this (all "average" classification). Demons also heavily depleted though (8 players out incl Viney, Salem).

**Signal:** Rules -27.7 looks too big — ML at -2.7 says this is genuinely close. If market has Bulldogs -15 to -22, **Melbourne cover or upset possible.** Total: unders lean (ML 165 vs rules 181).

| Result | Home (Bulldogs) | Away (Demons) | Total | Margin |
|--------|------|------|-------|--------|
| Actual | | | | |
| Rules pred | — | — | 181.5 | Bulldogs -27.7 |
| ML pred | — | — | 165.2 | Bulldogs -2.7 |
| Error | | | | |

---

## Round Summary & Signals

| Game | Rules H2H | ML H2H | Divergence | Signal |
|------|-----------|--------|------------|--------|
| Hawks vs Crows | Hawks 1.29 | Level | ◆◆◆ MAJOR | Fade Hawks / Crows cover |
| Tigers vs Bombers | Bombers 1.52 | Bombers | Aligned | Overs if market sub-155 |
| Dockers vs Saints | Dockers 1.10 | Dockers | ◆◆ margin | Saints cover — Darcy out, rules too wide |
| Kangaroos vs Suns | Suns 1.43 | Near-even | ◆◆◆ MAJOR | Kangaroos cover or upset |
| **Cats vs Swans** | Cats 1.77 | Cats (aligned) | ◆◆◆ TOTAL | **UNDERS ★★★** — ML 158 vs rules 209 |
| Magpies vs Eagles | Magpies 1.01 | Magpies | ◆ margin only | No value, Pies win easily |
| Power vs Blues | Power 1.26 | Power | Aligned | Low conf — Rozee absence watch |
| Giants vs Lions | Lions 1.37 | Near-even | ◆◆◆ MAJOR | Giants cover or upset |
| Bulldogs vs Demons | Bulldogs 1.28 | Near-even | ◆◆ margin | Demons cover — English out |

**Top signals this round:**
1. **Cats vs Swans UNDERS** — ML 158 vs rules 209, 51pt divergence. If market 170–185, strong unders.
2. **Giants cover vs Lions** — ML near-even, rules -22. Home ground, Lions depleted too.
3. **Kangaroos cover vs Suns** — ML near-even, rules -18.9. Three-metric divergence.
4. **Hawks vs Crows** — ML level, rules -27. Fade Hawks handicap.

---

*File generated: 2026-05-21 | Update Actual columns after each game*
*Rules = T1–T4 pure model. ML = XGBoost shadow (independent, not used in pricing). All prices fair (no margin).*
