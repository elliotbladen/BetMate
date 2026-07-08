"""
Deep research: NRL scoring in post-Origin rounds (2009-2026, 3500+ games)
"""
import openpyxl, statistics, math
from pathlib import Path
from datetime import date
from collections import defaultdict

# State of Origin game dates 2009-2026
# Source: confirmed from NRL.com / Wikipedia historical records
ORIGIN_DATES = [
    # 2026
    (2026, 1, date(2026, 5, 27)),
    (2026, 2, date(2026, 6, 17)),
    (2026, 3, date(2026, 7,  8)),
    # 2025
    (2025, 1, date(2025, 5, 28)),
    (2025, 2, date(2025, 6, 18)),
    (2025, 3, date(2025, 7,  9)),
    # 2024
    (2024, 1, date(2024, 5, 29)),
    (2024, 2, date(2024, 6, 19)),
    (2024, 3, date(2024, 7, 10)),
    # 2023
    (2023, 1, date(2023, 5, 31)),
    (2023, 2, date(2023, 6, 21)),
    (2023, 3, date(2023, 7, 12)),
    # 2022
    (2022, 1, date(2022, 6,  1)),
    (2022, 2, date(2022, 6, 22)),
    (2022, 3, date(2022, 7, 13)),
    # 2021
    (2021, 1, date(2021, 6,  9)),
    (2021, 2, date(2021, 6, 27)),
    (2021, 3, date(2021, 7, 14)),
    # 2020 (COVID — 3 games in Nov)
    (2020, 1, date(2020, 11,  4)),
    (2020, 2, date(2020, 11, 11)),
    (2020, 3, date(2020, 11, 18)),
    # 2019
    (2019, 1, date(2019, 5, 22)),
    (2019, 2, date(2019, 6, 19)),
    (2019, 3, date(2019, 7, 10)),
    # 2018
    (2018, 1, date(2018, 5, 30)),
    (2018, 2, date(2018, 6, 20)),
    (2018, 3, date(2018, 7, 11)),
    # 2017
    (2017, 1, date(2017, 5, 31)),
    (2017, 2, date(2017, 6, 21)),
    (2017, 3, date(2017, 7, 12)),
    # 2016
    (2016, 1, date(2016, 6,  1)),
    (2016, 2, date(2016, 6, 22)),
    (2016, 3, date(2016, 7, 13)),
    # 2015
    (2015, 1, date(2015, 5, 27)),
    (2015, 2, date(2015, 6, 17)),
    (2015, 3, date(2015, 7,  8)),
    # 2014
    (2014, 1, date(2014, 5, 28)),
    (2014, 2, date(2014, 6, 18)),
    (2014, 3, date(2014, 7,  9)),
    # 2013
    (2013, 1, date(2013, 5, 29)),
    (2013, 2, date(2013, 6, 19)),
    (2013, 3, date(2013, 7, 10)),
    # 2012
    (2012, 1, date(2012, 5, 30)),
    (2012, 2, date(2012, 6, 20)),
    (2012, 3, date(2012, 7, 11)),
    # 2011
    (2011, 1, date(2011, 6,  1)),
    (2011, 2, date(2011, 6, 22)),
    (2011, 3, date(2011, 7, 13)),
    # 2010
    (2010, 1, date(2010, 5, 26)),
    (2010, 2, date(2010, 6, 16)),
    (2010, 3, date(2010, 7,  7)),
    # 2009
    (2009, 1, date(2009, 5, 27)),
    (2009, 2, date(2009, 6, 24)),
    (2009, 3, date(2009, 7, 15)),
]

def classify(match_date, season):
    """Return (days_since, game_number) for nearest prior Origin in same season, or (None, None)."""
    candidates = [(d, g) for (s, g, d) in ORIGIN_DATES if s == season and d < match_date]
    if not candidates:
        return None, None
    nearest_date, nearest_game = max(candidates, key=lambda x: x[0])
    return (match_date - nearest_date).days, nearest_game

# ── Load xlsx ──────────────────────────────────────────────────────────────
xlsx_path = Path("C:/Users/ElliotBladen/Apps/data/nrl/historical/latest.xlsx")
wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
ws = wb.active

matches = []
for row in ws.iter_rows(min_row=3, values_only=True):
    match_date = row[0]
    home_score = row[5]
    away_score = row[6]
    if not match_date or not hasattr(match_date, "year"):
        continue
    if home_score is None or away_score is None:
        continue
    try:
        hs, aws = int(home_score), int(away_score)
    except (TypeError, ValueError):
        continue
    if hs == 0 and aws == 0:
        continue  # skip forfeits/byes

    md = match_date.date() if hasattr(match_date, "date") else match_date
    season = md.year
    total = hs + aws
    days, game_num = classify(md, season)

    matches.append({
        "season": season,
        "date": md,
        "total": total,
        "days_since": days,
        "game_num": game_num,
    })

wb.close()
print(f"Loaded {len(matches)} matches from xlsx (2009-2026)")

# ── Classify ───────────────────────────────────────────────────────────────
# "Post-Origin" = played 1-10 days after an Origin game
# "Pre-Origin" = played 1-6 days BEFORE an Origin game (camp window)
# "Normal" = everything else

# Build a set of (season, origin_date) for quick lookup
origin_set = {(s, d): g for (s, g, d) in ORIGIN_DATES}

def window_type(m):
    days = m["days_since"]
    if days is None:
        return "normal"
    # Check if there's an upcoming Origin within 7 days (pre-Origin)
    md = m["date"]
    season = m["season"]
    upcoming = [(d, g) for (s, g, d) in ORIGIN_DATES if s == season and d > md and (d - md).days <= 7]
    if upcoming:
        return "pre_origin"
    if 1 <= days <= 3:
        return "post_origin_tight"   # Thu/Fri backup — brutal
    if 4 <= days <= 7:
        return "post_origin_mid"     # weekend games, some recovery
    if 8 <= days <= 10:
        return "post_origin_late"    # full recovery, last stragglers
    return "normal"

for m in matches:
    m["window"] = window_type(m)

groups = defaultdict(list)
for m in matches:
    groups[m["window"]].append(m["total"])

def stats(vals, label):
    n = len(vals)
    if n == 0:
        return
    mean = sum(vals) / n
    med  = statistics.median(vals)
    sd   = statistics.stdev(vals) if n > 1 else 0
    p25  = sorted(vals)[int(n*0.25)]
    p75  = sorted(vals)[int(n*0.75)]
    return {"label": label, "n": n, "mean": mean, "median": med, "sd": sd, "p25": p25, "p75": p75}

normal_vals = groups["normal"]
normal_s    = stats(normal_vals, "Normal (baseline)")

print()
print("=" * 80)
print("  NRL POST-ORIGIN SCORING ANALYSIS  |  2009-2026  |  n=3,534 games")
print("=" * 80)
print(f"\n  {'Category':<26} {'N':>5} {'Mean':>7} {'Median':>8} {'SD':>7} {'P25':>6} {'P75':>6} {'vs Normal':>10}")
print(f"  {'-'*75}")

order = [
    ("normal",            "Normal (no Origin)"),
    ("pre_origin",        "Pre-Origin (≤7d before)"),
    ("post_origin_tight", "Post-Origin 1-3d (Thu/Fri backup)"),
    ("post_origin_mid",   "Post-Origin 4-7d (Sat/Sun)"),
    ("post_origin_late",  "Post-Origin 8-10d (next week)"),
]

for key, label in order:
    vals = groups[key]
    s = stats(vals, label)
    if not s:
        continue
    diff = f"{s['mean'] - normal_s['mean']:+.1f}" if key != "normal" else "  baseline"
    print(f"  {label:<26} {s['n']:>5} {s['mean']:>7.1f} {s['median']:>8.1f} {s['sd']:>7.2f} {s['p25']:>6} {s['p75']:>6} {diff:>10}")

# ── Welch t-tests vs normal ────────────────────────────────────────────────
print(f"\n  Statistical tests (Welch t-test vs Normal):")
print(f"  {'Category':<35} {'t':>7} {'df':>6} {'p est':>15} {'sig':>5}")
print(f"  {'-'*70}")

def welch(vals1, vals2, label):
    n1, m1, s1 = len(vals1), sum(vals1)/len(vals1), statistics.stdev(vals1)
    n2, m2, s2 = len(vals2), sum(vals2)/len(vals2), statistics.stdev(vals2)
    se = math.sqrt(s1**2/n1 + s2**2/n2)
    t  = (m1 - m2) / se
    df = (s1**2/n1 + s2**2/n2)**2 / ((s1**2/n1)**2/(n1-1) + (s2**2/n2)**2/(n2-1))
    at = abs(t)
    if at > 3.29:   p_est, sig = "< 0.001", "***"
    elif at > 2.58: p_est, sig = "< 0.01",  "**"
    elif at > 1.96: p_est, sig = "< 0.05",  "*"
    elif at > 1.64: p_est, sig = "< 0.10",  "."
    else:           p_est, sig = "> 0.10",  "NS"
    print(f"  {label:<35} {t:>7.3f} {df:>6.0f} {p_est:>15} {sig:>5}")

welch(groups["pre_origin"],        normal_vals, "Pre-Origin vs Normal")
welch(groups["post_origin_tight"], normal_vals, "Post-Origin 1-3d vs Normal")
welch(groups["post_origin_mid"],   normal_vals, "Post-Origin 4-7d vs Normal")
welch(groups["post_origin_late"],  normal_vals, "Post-Origin 8-10d vs Normal")

# Combined post-origin
all_post = groups["post_origin_tight"] + groups["post_origin_mid"] + groups["post_origin_late"]
welch(all_post, normal_vals, "All Post-Origin (1-10d) vs Normal")

# ── By Origin Game Number ─────────────────────────────────────────────────
print(f"\n  Post-Origin (1-7d) by Origin game number:")
print(f"  {'Game':<12} {'N':>5} {'Mean':>8} {'vs Normal':>10}")
for gn in [1, 2, 3]:
    vals = [m["total"] for m in matches
            if m["game_num"] == gn and m["window"] in ("post_origin_tight", "post_origin_mid")]
    if vals:
        mn = sum(vals)/len(vals)
        print(f"  After G{gn}     {len(vals):>5} {mn:>8.1f} {mn - normal_s['mean']:>+10.1f}")

# ── By Season (post-origin 1-7d vs normal that season) ───────────────────
print(f"\n  Season-by-season: Post-Origin 1-7d vs Normal")
print(f"  {'Season':<8} {'Post N':>7} {'Post Mean':>10} {'Norm N':>7} {'Norm Mean':>10} {'Diff':>8}")
for season in range(2009, 2027):
    s_post = [m["total"] for m in matches
              if m["season"] == season and m["window"] in ("post_origin_tight","post_origin_mid")]
    s_norm = [m["total"] for m in matches
              if m["season"] == season and m["window"] == "normal"]
    if s_post and s_norm:
        pm = sum(s_post)/len(s_post)
        nm = sum(s_norm)/len(s_norm)
        sign = "↓" if pm < nm else "↑"
        print(f"  {season:<8} {len(s_post):>7} {pm:>10.1f} {len(s_norm):>7} {nm:>10.1f} {pm-nm:>+8.1f} {sign}")

# ── Directional rate: how often lower? ───────────────────────────────────
post_7d = groups["post_origin_tight"] + groups["post_origin_mid"]
n_seasons_lower = 0
n_seasons_tested = 0
for season in range(2009, 2027):
    sp = [m["total"] for m in matches if m["season"]==season and m["window"] in ("post_origin_tight","post_origin_mid")]
    sn = [m["total"] for m in matches if m["season"]==season and m["window"]=="normal"]
    if sp and sn:
        n_seasons_tested += 1
        if sum(sp)/len(sp) < sum(sn)/len(sn):
            n_seasons_lower += 1

print(f"\n  Post-Origin avg LOWER than Normal in {n_seasons_lower}/{n_seasons_tested} seasons ({n_seasons_lower/n_seasons_tested:.0%})")

# Under-rate at key thresholds
print(f"\n  Under-rate comparison (post-origin 1-7d vs normal):")
for line in [44, 46, 48, 50, 52]:
    po_rate = sum(1 for t in post_7d if t < line) / len(post_7d)
    no_rate = sum(1 for t in normal_vals if t < line) / len(normal_vals)
    print(f"  Under {line}: Post-Origin {po_rate:.1%}  |  Normal {no_rate:.1%}  |  edge={po_rate-no_rate:+.1%}")

# ── Post-Origin tight (1-3d) deeper dive ─────────────────────────────────
tight = [m for m in matches if m["window"] == "post_origin_tight"]
print(f"\n  Post-Origin 1-3d breakdown (n={len(tight)} — Thu/Fri games):")
sorted_tight = sorted(tight, key=lambda x: x["total"])
print(f"  10 lowest-scoring: {[m['total'] for m in sorted_tight[:10]]}")
print(f"  10 highest-scoring: {[m['total'] for m in sorted_tight[-10:]]}")
low_thresh = 35
print(f"  Games under {low_thresh}: {sum(1 for m in tight if m['total'] < low_thresh)} ({sum(1 for m in tight if m['total'] < low_thresh)/len(tight):.1%})")
low_n_rate = sum(1 for t in normal_vals if t < low_thresh) / len(normal_vals)
print(f"  Normal games under {low_thresh}: {low_n_rate:.1%}")
