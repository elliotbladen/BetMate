"""
Research: does referee home ground bias affect TOTALS?

Three angles:
1. Do home wins score differently than away wins under each ref?
   (If Klein games produce higher-scoring home wins, there's a directional totals effect)
2. Correlation between penalty differential and game total score
   (Do refs who penalise away teams more also produce more/less scoring?)
3. Split totals by game outcome (home win / away win / draw) per referee
   Hypothesis: if home bias affects totals, we'd see totals skew in one direction
   under home-friendly refs.
4. Regression: does home_bias_adj explain any residual variance in totals
   beyond scoring_delta?
"""
import sqlite3, statistics

conn = sqlite3.connect("data/model.db")
conn.row_factory = sqlite3.Row

REFS = [
    ("Ashley Klein",   +3.20, -1.18),   # home_bias, scoring_delta
    ("Gerard Sutton",  -3.14, -1.06),
    ("Grant Atkins",   -0.05, -0.29),
    ("Adam Gee",       +0.72, -0.07),
    ("Todd Smith",     -0.79, +0.43),
    ("Peter Gough",    -0.13, +0.99),
    ("Wyatt Raymond",  +0.58, +3.13),
]

# Season averages for adjustment
season_avgs = {}
for row in conn.execute("""
    SELECT season, AVG(total_score) as avg_tot
    FROM referee_game_stats
    WHERE competition LIKE 'NRL Premiership%'
    GROUP BY season
""").fetchall():
    season_avgs[row["season"]] = row["avg_tot"]

print("Season averages (all 7 refs):")
for yr, avg in sorted(season_avgs.items()):
    print(f"  {yr}: {avg:.1f}")

# -----------------------------------------------------------------------
# ANGLE 1: Totals split by home win / away win under each referee
# -----------------------------------------------------------------------
print()
print("=" * 90)
print("ANGLE 1 — Total score by game outcome per referee (season-adjusted residuals)")
print("=" * 90)
print(f"  {'Referee':<26} {'bias':>6} {'Home-win tot':>13} {'Away-win tot':>13} {'Diff':>8} {'N(H)':>6} {'N(A)':>6}")
print("-" * 90)

for ref_name, bias, scoring_delta in REFS:
    rows = conn.execute("""
        SELECT season, home_score, away_score, total_score
        FROM referee_game_stats
        WHERE referee_name=? AND competition LIKE 'NRL Premiership%'
    """, (ref_name,)).fetchall()

    home_win_resids = []
    away_win_resids = []
    for r in rows:
        resid = r["total_score"] - season_avgs.get(r["season"], 46)
        if r["home_score"] > r["away_score"]:
            home_win_resids.append(resid)
        elif r["away_score"] > r["home_score"]:
            away_win_resids.append(resid)

    hw_avg = statistics.mean(home_win_resids) if home_win_resids else 0
    aw_avg = statistics.mean(away_win_resids) if away_win_resids else 0
    diff   = hw_avg - aw_avg

    print(f"  {ref_name:<26} {bias:>+5.2f}  {hw_avg:>+11.2f}   {aw_avg:>+11.2f}  {diff:>+7.2f}  {len(home_win_resids):>5}  {len(away_win_resids):>5}")

# -----------------------------------------------------------------------
# ANGLE 2: Penalty count vs total score correlation per referee
# -----------------------------------------------------------------------
print()
print("=" * 90)
print("ANGLE 2 — Penalty count vs total score correlation (by referee)")
print("=" * 90)
print(f"  {'Referee':<26} {'bias':>6} {'Corr(pen,total)':>16} {'Avg home pen':>13} {'Avg away pen':>13}")
print("-" * 90)

for ref_name, bias, scoring_delta in REFS:
    rows = conn.execute("""
        SELECT season, total_score, home_penalties, away_penalties, total_penalties
        FROM referee_game_stats
        WHERE referee_name=? AND competition LIKE 'NRL Premiership%'
          AND total_penalties IS NOT NULL AND total_penalties > 0
    """, (ref_name,)).fetchall()

    if len(rows) < 10:
        continue

    totals  = [r["total_score"] for r in rows]
    pens    = [r["total_penalties"] for r in rows]
    h_pens  = [r["home_penalties"] for r in rows]
    a_pens  = [r["away_penalties"] for r in rows]

    # Pearson correlation
    n = len(totals)
    mean_t = statistics.mean(totals)
    mean_p = statistics.mean(pens)
    cov = sum((t - mean_t) * (p - mean_p) for t, p in zip(totals, pens)) / n
    std_t = statistics.stdev(totals)
    std_p = statistics.stdev(pens)
    corr = cov / (std_t * std_p) if std_t and std_p else 0

    avg_hp = statistics.mean(h_pens)
    avg_ap = statistics.mean(a_pens)

    print(f"  {ref_name:<26} {bias:>+5.2f}  {corr:>+14.3f}   {avg_hp:>11.2f}   {avg_ap:>11.2f}")

# -----------------------------------------------------------------------
# ANGLE 3: Does home bias explain totals variance AFTER removing scoring_delta?
# -----------------------------------------------------------------------
print()
print("=" * 90)
print("ANGLE 3 — Residual totals variance: home bias refs vs neutral refs")
print("  (After removing scoring_delta from totals, does home/away result change things?)")
print("=" * 90)

# Pool all games, compute residual = total - season_avg - scoring_delta
# Then split by: [home-biased ref + home wins] vs [away-biased ref + away wins]
klein_rows   = conn.execute("SELECT * FROM referee_game_stats WHERE referee_name='Ashley Klein' AND competition LIKE 'NRL Premiership%'").fetchall()
sutton_rows  = conn.execute("SELECT * FROM referee_game_stats WHERE referee_name='Gerard Sutton' AND competition LIKE 'NRL Premiership%'").fetchall()
neutral_rows = conn.execute("SELECT * FROM referee_game_stats WHERE referee_name IN ('Grant Atkins','Adam Gee','Todd Smith','Peter Gough') AND competition LIKE 'NRL Premiership%'").fetchall()

def resid_by_outcome(rows, scoring_delta, label):
    home_wins, away_wins = [], []
    for r in rows:
        res = r["total_score"] - season_avgs.get(r["season"], 46) - scoring_delta
        if r["home_score"] > r["away_score"]:
            home_wins.append(res)
        else:
            away_wins.append(res)
    hw = statistics.mean(home_wins) if home_wins else 0
    aw = statistics.mean(away_wins) if away_wins else 0
    print(f"  {label}")
    print(f"    Home wins: {hw:>+.2f} pts above expected  (n={len(home_wins)})")
    print(f"    Away wins: {aw:>+.2f} pts above expected  (n={len(away_wins)})")
    print(f"    Diff (hw-aw): {hw-aw:>+.2f} — {'YES directional effect' if abs(hw-aw) > 2.0 else 'no meaningful directional effect'}")

resid_by_outcome(klein_rows,  -1.18, "Klein (+3.20 home bias, -1.18 scoring_delta)")
resid_by_outcome(sutton_rows, -1.06, "Sutton (-3.14 home bias, -1.06 scoring_delta)")
resid_by_outcome(neutral_rows, 0.0,  "Neutral refs combined (Atkins, Gee, Smith, Gough)")

# -----------------------------------------------------------------------
# ANGLE 4: Summary verdict
# -----------------------------------------------------------------------
print()
print("=" * 90)
print("VERDICT: Does home ground bias require a separate totals adjustment?")
print("=" * 90)
print("""
  The scoring_delta already captures each ref's total-score environment.
  The question here is whether the HOME BIAS effect (who wins) also shifts
  the total INDEPENDENTLY of that baseline.

  To answer: if home-win games under Klein score differently than away-win
  games under Klein, beyond what the scoring_delta already accounts for,
  then we need a second totals correction linked to home bias direction.

  If there is NO difference → the scoring_delta is the only totals lever
  and home_bias only affects handicap (as currently implemented).
""")

conn.close()
