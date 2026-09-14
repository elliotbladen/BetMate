# 2026-09-14 — NRL matrix retirement (end-of-2026-season review)

Branch `chore/nrl-matrix-retirement-2027`. Owner's call after the AFL matrix work:
*"this is a end of season review with nrl. so yep, next season we won't be using it."*

**Outcome: the NRL base-rate matrices are out of the pricing pipeline and off the
website. AFL is untouched and stays live for totals.**

## Evidence gathered BEFORE removing anything

The published NRL study walked forward **totals only, to net +7**. Its h2h (−26.9%)
and handicap (−5.0%) figures were **2026 alone**, never walked forward. The AFL study
held every market to a 9-season walk-forward, so NRL was brought to the same standard
first — removing on one season of evidence is the error pattern this repo keeps hitting.

`scripts/nrl_h2h_matrix.py` and `nrl_handicap_matrix.py` were parameterised with
`--seasons/--source/--out` (**regression-gated: h2h 7,530 cells, handicap 1,204 rows,
zero differences**), and `walkforward_nrl_matrix.py` was rewritten to cover all three
markets. It drives the **unmodified** backtest, rebinding matrix constants in-process
for h2h/handicap so production artefacts are never touched. `--validate` reproduces the
published totals row and **exits non-zero** on mismatch.

### ⚠️ A data gap found mid-analysis, which changed the numbers

The NRL history is **missing H2H and LINE-ODDS closing prices for 70% of 2024 (64/213)
and 99.5% of 2025 (1/213)**. Totals coverage is complete throughout.

On the first run those seasons entered as **silent zeros** — 2025 produced 0 bets and
reported "+0.00% ROI", which reads as a flat season rather than as no data. Caught
because +0.0% appeared in *every* h2h/handicap configuration, which is not how real
results behave. DATA_INTEGRITY_LESSONS #8 landing live. `--skip-seasons` was added and
all h2h/handicap figures exclude 2024-25.

### Results

| market | net | pooled ROI | n | 95% CI | seasons +ve |
|---|---|---|---|---|---|
| h2h | +7 | −4.95% | 449 | [−12.4, +2.7] | 2/8 |
| h2h | +10 | +0.26% | 161 | [−11.5, +12.5] | 5/8 |
| **handicap** | **+7** | **−12.52%** | 419 | **[−21.7, −3.4]** | **0/8** |
| handicap | +10 | −11.96% | 136 | [−27.6, +4.4] | 2/8 |
| totals | +8→+12 open | −3.49% to +6.36% | 70-446 | all straddle zero | 5-6/10 |

**Handicap loses significantly** (CI excludes zero, negative 8/8 seasons). h2h and
totals sit on zero. **No market shows a dose-response** — the specific property AFL
totals does show, and the reason AFL survived where NRL did not.

## What was removed

**Engine**
- `prepare_round.py` — Step 8 (regenerate matrices) + Step 9 (push to Supabase), the
  `_parse_edge` / `_xlsx_to_matrix` / `_handicap_csv_to_matrix` helpers, the unused
  `utils.supabase_push` import, and the `--skip-matrices` flag that only gated them.
  An in-place comment carries the measured reason so it is not re-added blind.
- `push_matrices_to_supabase.py` — deleted (NRL-only; pushed all three files).
- `matrix_confluence.py` — retirement banner, kept as research tooling.

**Web** — these were fed *exclusively* by the NRL matrices, so with the matrices gone
the route could only ever return `{ signals: [] }`, and a permanently-empty feature
reporting success is exactly this codebase's characteristic failure.
- `app/api/ev-signals/route.ts`, `lib/matrixEV.ts` — deleted.
- `GameCard.tsx` — EVSignal import, evSignals state + fetch, pickSignal/freeEV, the
  per-market lookups, the per-tab signal dot, free/PRO edge badges, the "No value edge
  detected" placeholder, the NRL disclaimer, and the ev props passed to the three rows.
- `proxy.ts` — `/api/ev-signals` out of PUBLIC_PATHS.

**Side benefit:** this permanently removes the route that caused the **2.49GB
function-tracing deploy failure** that blocked Vercel for days. `outputFileTracingExcludes`
stays as a repo-wide guard; its comment referenced the deleted matrixEV and was corrected.

## What was kept, deliberately

- The NRL **builders, backtest and walk-forward** — the evidence trail, so the question
  can be re-opened with data rather than rebuilt from scratch.
- The public-% and line-move badges that shared the value-edge strip. The strip now
  renders **only when it has content**, so it is not an empty bordered bar.
- `OddsRow`/`SpreadsRow`/`TotalsRow` still accept their optional `ev*` props; nothing
  passes them. Left alone to keep the diff at the data boundary.
- ⚠️ **AFL matrices entirely** — `afl_matrix_confluence.py`, the AFL builders and the
  AFL v2 totals matrix all stay live.

## Verification

- BettingEngine pytest: **244 pass**, same 3 pre-existing pyarrow failures.
- `npm run build`: **exit 0** (clean `.next`).
- `npx tsc --noEmit`: **exit 0**.
- `eslint .`: exit 1 with **61 problems — unchanged from baseline**.
- `/api/ev-signals` no longer appears in the route manifest.
- `prepare_round.py --help` runs; `--skip-matrices` gone, all other flags intact.

## Next

- ⚠️ **The 2024/2025 h2h + line-odds gap in the NRL history is still open.** Totals are
  fine; h2h/handicap closing prices are largely missing for two seasons. Worth a
  backfill from `data/odds_snapshots/` if those markets are ever re-examined.
- The UI has **still not been visually checked in a browser** since Next 16, and the
  odds board just lost a strip. The build passes and the empty-state path was already
  there, but a click-through at 375px is worth doing.
- Supabase still holds the old `nrl_h2h_matrix` / `nrl_totals_matrix` /
  `nrl_handicap_matrix` keys. Nothing reads them now; they can be dropped whenever.
