import csv, sqlite3
from pathlib import Path
from collections import defaultdict

ROOT = Path("C:/Users/ElliotBladen/Apps")
BE   = ROOT / "BettingEngine"

# ── 1. Model totals from pricing CSVs ──────────────────────────────────────
model_totals = defaultdict(list)

pricing_map = {
    9:  BE / "results/r9_pricing_2026.csv",
    10: BE / "results/r10_pricing_2026.csv",
    11: BE / "results/r11_pricing_2026.csv",
    12: BE / "results/r12_pricing_2026.csv",
    13: BE / "results/r13_pricing_2026.csv",
    14: BE / "results/r14_pricing_2026.csv",
    15: BE / "results/r15_pricing_2026.csv",
    16: BE / "results/r16_pricing_2026.csv",
}

# R8 — check data/pricing/nrl/
alt_r8 = sorted((BE / "data/pricing/nrl").glob("NRL_PRICING_R08*.csv"))
if alt_r8:
    # exclude tier_breakdown and ml_shadow
    r8_candidates = [f for f in alt_r8 if "tier_breakdown" not in f.name and "ml_shadow" not in f.name]
    if r8_candidates:
        pricing_map[8] = r8_candidates[0]

for rnd in sorted(pricing_map):
    fpath = pricing_map[rnd]
    if not fpath.exists():
        print(f"R{rnd}: pricing file NOT FOUND ({fpath.name})")
        continue
    rows = list(csv.DictReader(open(fpath, encoding="utf-8-sig", errors="replace")))
    totals = [float(r["final_total"]) for r in rows if r.get("final_total")]
    model_totals[rnd] = totals

# ── 2. Actual totals from model.db ─────────────────────────────────────────
actual_totals = defaultdict(list)
db_actual_games = defaultdict(set)

db_path = BE / "data/model.db"
if db_path.exists():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT m.round_number as round, r.total_score AS total
            FROM results r
            JOIN matches m ON m.match_id = r.match_id
            WHERE m.season = 2026 AND m.round_number >= 8
            ORDER BY m.round_number, m.match_id
        """)
        for row in cur.fetchall():
            rnd = int(row["round"])
            actual_totals[rnd].append(int(row["total"]))
    except Exception as e:
        print(f"[DB] Error: {e}")
    conn.close()

# ── 3. Market opening/closing totals lines from CLV files ─────────────────
market_open  = defaultdict(list)
market_close = defaultdict(list)

clv_dir = BE / "data/clv/nrl"
all_clv = sorted(clv_dir.glob("*.csv"))

for f in all_clv:
    if "tier_breakdown" in f.name or "ml_shadow" in f.name:
        continue
    try:
        rows = list(csv.DictReader(open(f, encoding="utf-8-sig", errors="replace")))
    except Exception:
        continue
    for r in rows:
        rnd_raw = r.get("round", "")
        market  = r.get("market", "").lower()
        if not rnd_raw or market not in ("totals", "total"):
            continue
        rnd = int(rnd_raw)
        open_n  = r.get("open_number", "").strip()
        close_n = r.get("close_number", "").strip()
        if open_n:
            try:
                market_open[rnd].append(float(open_n))
            except ValueError:
                pass
        if close_n:
            try:
                market_close[rnd].append(float(close_n))
            except ValueError:
                pass

# Also pull actual totals from CLV files as a cross-check
clv_actuals = defaultdict(set)
clv_actual_vals = defaultdict(list)
for f in all_clv:
    try:
        rows = list(csv.DictReader(open(f, encoding="utf-8-sig", errors="replace")))
    except Exception:
        continue
    for r in rows:
        rnd_raw = r.get("round", "")
        if not rnd_raw:
            continue
        rnd = int(rnd_raw)
        home = r.get("home_team", "")
        away = r.get("away_team", "")
        actual = r.get("actual_total", "").strip()
        key = (home, away)
        if actual and key not in clv_actuals[rnd]:
            try:
                clv_actuals[rnd].add(key)
                clv_actual_vals[rnd].append(float(actual))
            except ValueError:
                pass

# Merge: prefer DB actuals; fill gaps with CLV actuals
for rnd in range(8, 17):
    if not actual_totals.get(rnd) and clv_actual_vals.get(rnd):
        actual_totals[rnd] = clv_actual_vals[rnd]

# ── 4. Get full-season league average from DB (all R1+ games with results) ─
league_all_totals = []
if db_path.exists():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT (r.home_score + r.away_score) AS total
            FROM results r
            JOIN matches m ON m.match_id = r.match_id
            WHERE m.season = 2026
        """)
        league_all_totals = [int(row["total"]) for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB League] {e}")
    conn.close()

# ── 5. Print table ──────────────────────────────────────────────────────────
print()
print("=" * 95)
print(f"  NRL 2026 TOTALS COMPARISON — R8 to R16")
print("=" * 95)
print(f"  {'Rnd':<5} {'Games':>5}  {'Model Avg':>10}  {'Mkt Open':>9}  {'Mkt Close':>10}  {'Actual Avg':>11}  {'Mdl-Open':>9}  {'Mdl-Close':>10}  {'Mdl-Actual':>11}")
print("-" * 95)

all_model, all_open, all_close, all_actual_flat = [], [], [], []

for rnd in range(8, 17):
    m = model_totals.get(rnd, [])
    o = market_open.get(rnd, [])
    c = market_close.get(rnd, [])
    a = actual_totals.get(rnd, [])

    m_avg = sum(m)/len(m) if m else None
    o_avg = sum(o)/len(o) if o else None
    c_avg = sum(c)/len(c) if c else None
    a_avg = sum(a)/len(a) if a else None

    n_games = len(m) if m else (len(a) if a else 0)

    if m: all_model.extend(m)
    if o: all_open.extend(o)
    if c: all_close.extend(c)
    if a: all_actual_flat.extend(a)

    def f1(v):  return f"{v:10.1f}" if v is not None else f"{'—':>10}"
    def fd(v):  return f"{v:+10.1f}" if v is not None else f"{'—':>10}"

    mo_diff = (m_avg - o_avg) if (m_avg and o_avg) else None
    mc_diff = (m_avg - c_avg) if (m_avg and c_avg) else None
    ma_diff = (m_avg - a_avg) if (m_avg and a_avg) else None

    flag = " ⏳" if rnd == 16 else ""
    print(f"  R{rnd:<4}{flag} {n_games:>5}  {f1(m_avg)}  {f1(o_avg)}  {f1(c_avg)}  {f1(a_avg)}  {fd(mo_diff)}  {fd(mc_diff)}  {fd(ma_diff)}")

print("-" * 95)
gm  = sum(all_model)/len(all_model) if all_model else None
go  = sum(all_open)/len(all_open)   if all_open  else None
gc  = sum(all_close)/len(all_close) if all_close else None
ga  = sum(all_actual_flat)/len(all_actual_flat) if all_actual_flat else None
gmo = (gm - go) if (gm and go) else None
gmc = (gm - gc) if (gm and gc) else None
gma = (gm - ga) if (gm and ga) else None

print(f"  {'SEASON':5}  {len(all_model):>5}  {f1(gm)}  {f1(go)}  {f1(gc)}  {f1(ga)}  {fd(gmo)}  {fd(gmc)}  {fd(gma)}")
print("=" * 95)

if league_all_totals:
    league_avg = sum(league_all_totals) / len(league_all_totals)
    print(f"\n  League avg (all 2026 games with results, R1+): {league_avg:.1f}  (n={len(league_all_totals)})")
    print(f"  R8-R16 actual avg:  {ga:.1f}" if ga else "")
    if gm and league_avg:
        print(f"  Model avg vs league avg: {gm - league_avg:+.1f}")
    if gc and league_avg:
        print(f"  Market close avg vs league avg: {gc - league_avg:+.1f}")

print(f"\n  Interpretation:")
print(f"  Mdl-Close: positive = model runs HIGH vs closing line (market expected less scoring)")
print(f"  Mdl-Actual: positive = model over-predicted; negative = model under-predicted actual scoring")
