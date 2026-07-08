"""
Referee home ground bias analysis.

For each referee, measures:
1. avg home margin (home_score - away_score) vs season-adjusted baseline
2. home win rate vs league average
3. home penalty differential (away_penalties - home_penalties)
   positive = ref blows against away team (home-friendly)
   negative = ref blows against home team (away-friendly)

Season adjustment removes the NRL-wide trend.
"""
import sqlite3

conn = sqlite3.connect("data/model.db")
conn.row_factory = sqlite3.Row

# -----------------------------------------------------------------
# Step 1: season averages (all 7 refs combined = league baseline)
# -----------------------------------------------------------------
seasons = conn.execute("""
    SELECT season,
           AVG(home_score - away_score)    AS avg_home_margin,
           AVG(CAST(home_score > away_score AS INT)) AS home_win_rate,
           AVG(away_penalties - home_penalties)      AS avg_pen_diff
    FROM referee_game_stats
    WHERE competition LIKE 'NRL Premiership%'
    GROUP BY season
    ORDER BY season
""").fetchall()

print("=== SEASON BASELINES (all 7 refs, NRL Premiership) ===")
print(f"{'Season':>8} {'Avg Home Margin':>16} {'Home Win %':>12} {'Pen Diff (A-H)':>16}")
for s in seasons:
    print(f"  {s['season']:>6}  {s['avg_home_margin']:>14.2f}  {s['home_win_rate']*100:>10.1f}%  {s['avg_pen_diff']:>14.2f}")

season_lookup = {s['season']: dict(s) for s in seasons}

# -----------------------------------------------------------------
# Step 2: per-referee stats with season adjustment
# -----------------------------------------------------------------
refs = [
    "Ashley Klein", "Gerard Sutton", "Grant Atkins",
    "Adam Gee", "Todd Smith", "Peter Gough", "Wyatt Raymond"
]

print()
print("=== REFEREE HOME BIAS (season-adjusted) ===")
print(f"{'Referee':<28} {'N':>4} {'Raw Margin':>12} {'Adj Margin':>12} {'Home Win%':>10} {'Pen Diff':>10}  Verdict")
print("-" * 100)

results = []
for ref in refs:
    rows = conn.execute("""
        SELECT season, home_score, away_score,
               home_penalties, away_penalties
        FROM referee_game_stats
        WHERE referee_name = ? AND competition LIKE 'NRL Premiership%'
        ORDER BY season
    """, (ref,)).fetchall()

    if not rows:
        continue

    n = len(rows)
    raw_margins = [(r['home_score'] - r['away_score']) for r in rows]
    home_wins   = [1 if r['home_score'] > r['away_score'] else 0 for r in rows]
    pen_diffs   = [(r['away_penalties'] - r['home_penalties']) for r in rows
                   if r['away_penalties'] is not None and r['home_penalties'] is not None]

    # Season-adjusted margin residual
    adj_margins = []
    for r in rows:
        base = season_lookup.get(r['season'], {}).get('avg_home_margin', 0)
        adj_margins.append((r['home_score'] - r['away_score']) - base)

    raw_avg  = sum(raw_margins) / n
    adj_avg  = sum(adj_margins) / n
    win_rate = sum(home_wins) / n * 100
    pen_avg  = sum(pen_diffs) / len(pen_diffs) if pen_diffs else 0.0

    # Verdict
    if adj_avg >= 1.5:
        verdict = "HOME-FRIENDLY"
    elif adj_avg <= -1.5:
        verdict = "AWAY-FRIENDLY"
    else:
        verdict = "neutral"

    results.append({
        'name': ref, 'n': n,
        'raw': raw_avg, 'adj': adj_avg,
        'win_rate': win_rate, 'pen_avg': pen_avg,
        'verdict': verdict
    })

    print(f"  {ref:<26} {n:>4}  {raw_avg:>10.2f}  {adj_avg:>+10.2f}  {win_rate:>8.1f}%  {pen_avg:>+8.2f}  {verdict}")

# -----------------------------------------------------------------
# Step 3: home win rate comparison to league baseline
# -----------------------------------------------------------------
league_home_win = conn.execute("""
    SELECT AVG(CAST(home_score > away_score AS INT)) AS rate
    FROM referee_game_stats
    WHERE competition LIKE 'NRL Premiership%'
""").fetchone()['rate'] * 100

print()
print(f"  League average home win rate (all 7 refs, 2022-2026): {league_home_win:.1f}%")

# -----------------------------------------------------------------
# Step 4: penalty differential breakdown by season for top movers
# -----------------------------------------------------------------
print()
print("=== PENALTY DIFFERENTIAL BY SEASON (away_pen - home_pen, positive = home team favoured) ===")
print(f"{'Referee':<28} {'2022':>8} {'2023':>8} {'2024':>8} {'2025':>8} {'2026':>8} {'Overall':>10}")
print("-" * 90)

for ref in refs:
    row_data = {}
    for yr in [2022, 2023, 2024, 2025, 2026]:
        rows_yr = conn.execute("""
            SELECT away_penalties - home_penalties AS pd
            FROM referee_game_stats
            WHERE referee_name=? AND competition LIKE 'NRL Premiership%' AND season=?
              AND away_penalties IS NOT NULL AND home_penalties IS NOT NULL
        """, (ref, yr)).fetchall()
        if rows_yr:
            row_data[yr] = sum(r['pd'] for r in rows_yr) / len(rows_yr)

    overall = conn.execute("""
        SELECT AVG(away_penalties - home_penalties) AS pd
        FROM referee_game_stats
        WHERE referee_name=? AND competition LIKE 'NRL Premiership%'
          AND away_penalties IS NOT NULL AND home_penalties IS NOT NULL
    """, (ref,)).fetchone()['pd'] or 0

    cells = "".join(f"{row_data.get(yr, 0):>+8.2f}" for yr in [2022, 2023, 2024, 2025, 2026])
    print(f"  {ref:<26}{cells}  {overall:>+8.2f}")

print()
print("  Penalty diff = avg(away_penalties - home_penalties)")
print("  Positive = ref gives MORE penalties to away team = home-friendly")
print("  Negative = ref gives MORE penalties to home team = away-friendly")

conn.close()
