# Session Diary — 2026-06-11
## Closing Price Fills for MODEL_BETS ids 19-25

---

### What was done this session

Filled `closingPrice` for MODEL_BETS ids 19-25 in `lib/researchData.ts`.

These were the R7/R8 era bets (April 16 and April 24, 2026) that had no CLV file because the CLV tracking system only started at R9. The closing prices were sourced from `data/nrl/historical/latest.xlsx` (aussportsbetting full historical file).

**Column mapping used from xlsx (row 2 headers, 0-indexed):**
- Col 20: Away Odds Close (H2H)
- Col 32: Home Line Odds Close (handicap home side)
- Col 48: Total Score Under Close

**Closing prices applied:**

| id | Match | Market | Taken | Close | Notes |
|----|-------|--------|-------|-------|-------|
| 19 | Cowboys vs Manly | Under 53.5 | 1.90 | 1.85 | Total closed 54.5 |
| 20 | Dolphins vs Penrith | Under 51.5 | 1.90 | 1.85 | Total closed 52.5 |
| 21 | Parramatta vs Canterbury | Parramatta +13.5 | 1.90 | 1.85 | Hcap closed +12.5 @ 1.85 |
| 22 | Rabbitohs vs St George | Under 51.5 | 1.90 | 1.95 | Exact same line |
| 23 | Wests vs Brisbane | Brisbane Win | 2.50 | 2.45 | Brisbane = away team |
| 24 | Wests vs Canberra | Canberra Win | 2.00 | 2.65 | −24.5% CLV — big loss |
| 25 | Wests vs Canberra | Under 52.5 | 1.90 | 2.05 | Total closed 48.5 (line diff) |

**id:26 left null** — "St George vs Penrith, St George Win" dated April 24. Checked all St George games in 2026: no St George vs Penrith exists in April. Only one exists all season (May 17, St George at 9.50 — completely wrong market). The match label may be wrong. If the actual game is identified, close can be filled from xlsx.

---

### CLV note on id:24

Canberra Win @ 2.00 vs close of 2.65 = **−24.5% CLV**. This is the worst CLV bet in the R8/R9 period. The market knew something — Tigers were 1.48 at close, implying Tigers were very firm. Tigers won 33-14. Taking Canberra at 2.00 when they closed at 2.65 was badly timed.

---

### Git

Commit `885ee93` — "Fill closingPrice for MODEL_BETS ids 19-25 from aussportsbetting xlsx"
Pushed to main → auto-deployed to betmate.au

---

### Pending / Carry-forward

- **id:26 closingPrice**: identify the actual game or confirm match label is wrong
- **G2 Origin squads**: Camp started Jun 12 — populate `data/nrl/origin/2026.json` before R15 pricing
- **R14 CLV**: NRL R14 + AFL R13 closing lines needed before running pipeline scripts
- **Custom domain betmate.au**: www CNAME fix pending
- **Refs on Vercel**: Wire `lib/referees.ts` to Supabase key
- **AFL sigmoid ELO scaling**: Replace linear POINTS_PER_ELO (next AFL session)
