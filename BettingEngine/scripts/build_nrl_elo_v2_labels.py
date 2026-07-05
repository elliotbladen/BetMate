#!/usr/bin/env python3
"""
Build NRL Elo v2 luck/performance labels from match stats and report snippets.

The label is intentionally structured:
  - scoreboard result stays primary
  - stats identify round-level "this result was noisy" games
  - reports are attached as context, not used as the primary scorer

Output is training/audit data for Elo v2 experiments, not a database write.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

STAT_WEIGHTS = {
    "line_breaks": 3.0,
    "try_assists": 2.0,
    "run_metres": 0.010,
    "post_contact_metres": 0.015,
    "tackle_busts": 0.15,
    "tackledOpp20": 0.08,
    "forced_drop_outs": 0.50,
    "possession_percentage": 0.25,
    "territory": 0.20,
    "complete_sets": 0.25,
    "errors": -0.60,
    "inCompleteSets": -0.50,
    "penalties_conceded": -0.25,
    "missed_tackles": -0.15,
    "sin_bins": -2.0,
}

NOTE_STATS = [
    "line_breaks",
    "try_assists",
    "run_metres",
    "post_contact_metres",
    "tackle_busts",
    "tackledOpp20",
    "forced_drop_outs",
    "possession_percentage",
    "territory",
    "complete_sets",
    "errors",
    "inCompleteSets",
    "penalties_conceded",
    "missed_tackles",
    "sin_bins",
]

TEAM_CANON = {
    "Brisbane": "Brisbane Broncos",
    "Canberra": "Canberra Raiders",
    "Canterbury": "Canterbury-Bankstown Bulldogs",
    "Cronulla": "Cronulla-Sutherland Sharks",
    "Gold Coast Titans": "Gold Coast Titans",
    "Manly": "Manly-Warringah Sea Eagles",
    "Melbourne": "Melbourne Storm",
    "Melbourne Storm": "Melbourne Storm",
    "Newcastle": "Newcastle Knights",
    "North Queensland": "North Queensland Cowboys",
    "Parramatta": "Parramatta Eels",
    "Penrith": "Penrith Panthers",
    "Penrith Panthers": "Penrith Panthers",
    "South Sydney": "South Sydney Rabbitohs",
    "St George Illawarra": "St. George Illawarra Dragons",
    "Sydney Roosters": "Sydney Roosters",
    "Warriors": "New Zealand Warriors",
    "Wests Tigers": "Wests Tigers",
    "Dolphins": "Dolphins",
}

REPORT_CONTEXT_TERMS = [
    "controversial",
    "bunker",
    "penalty try",
    "sin bin",
    "sent off",
    "injury",
    "head knock",
    "hia",
    "no try",
    "late",
    "intercept",
    "against the run of play",
    "comeback",
]


def canon_team(name: str) -> str:
    return TEAM_CANON.get(name, name)


def stat(stats: dict, key: str) -> float:
    value = stats.get(key)
    if value in (None, ""):
        return 0.0
    return float(value)


def stat_dominance(a_stats: dict, b_stats: dict) -> float:
    return round(
        sum((stat(a_stats, key) - stat(b_stats, key)) * weight for key, weight in STAT_WEIGHTS.items()),
        2,
    )


def load_reports(path: Path, season: int) -> dict[tuple[int, int, int], list[dict]]:
    reports: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    if not path.exists():
        return reports

    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if int(row.get("season") or 0) != season:
                continue
            key = (int(row["season"]), int(row["round_number"]), int(row["game_number"]))
            reports[key].append(row)
    return reports


def report_context(rows: list[dict]) -> tuple[str, str, str]:
    if not rows:
        return "", "", ""

    titles = []
    snippets = []
    hits = set()
    for row in rows:
        title = row.get("title", "").strip()
        excerpt = row.get("excerpt", "").strip()
        description = row.get("description", "").strip()
        if title:
            titles.append(title)
        text = f"{title} {description} {excerpt}".lower()
        for term in REPORT_CONTEXT_TERMS:
            if term in text:
                hits.add(term)
        source = row.get("source", "").strip()
        if excerpt:
            snippets.append(f"{source}: {excerpt[:240]}")
    return " | ".join(sorted(hits)), " || ".join(titles[:2]), " || ".join(snippets[:2])


def winner_side(score_margin: float) -> str:
    if score_margin == 0:
        return ""
    return "A" if score_margin > 0 else "B"


def loser_side(score_margin: float) -> str:
    if score_margin == 0:
        return ""
    return "B" if score_margin > 0 else "A"


def side_name(side: str, a_name: str, b_name: str) -> str:
    return a_name if side == "A" else b_name


def winner_dominance(score_margin: float, dominance_a: float) -> float:
    if score_margin == 0:
        return 0.0
    return dominance_a if score_margin > 0 else -dominance_a


def adjustment_score(score_margin: float, dominance_a: float, report_terms: str) -> tuple[str, float]:
    """
    Score how much this game deserves an Elo dampener.

    Types:
      stat_reversal: loser won the stat profile.
      margin_exaggeration: winner won, but stats do not support the scoreboard margin.
      report_context_tension: reports mention noisy context in a close/weak-stat game.
    """
    if score_margin == 0:
        return "normal", 0.0

    close_game_bonus = max(0.0, 14.0 - abs(score_margin)) * 0.35
    winner_dom = winner_dominance(score_margin, dominance_a)

    if score_margin > 0 and dominance_a < 0:
        return "stat_reversal", abs(dominance_a) + close_game_bonus
    if score_margin < 0 and dominance_a > 0:
        return "stat_reversal", abs(dominance_a) + close_game_bonus

    if abs(score_margin) >= 14 and winner_dom < 8:
        return "margin_exaggeration", (abs(score_margin) - max(winner_dom, 0.0)) * 0.65

    if abs(score_margin) <= 8 and winner_dom < 8:
        context_bonus = 4.0 if report_terms else 0.0
        return "close_game_tension", (8.0 - max(winner_dom, 0.0)) + close_game_bonus + context_bonus

    if report_terms and abs(score_margin) <= 10 and winner_dom < 12:
        return "report_context_tension", 6.0 + close_game_bonus

    return "normal", 0.0


def classify_candidate(score_margin: float, dominance_a: float, report_terms: str) -> tuple[str, str, str, str, float]:
    """Return adjustment type, hard-done-by side, lucky winner side, action, severity."""
    adj_type, severity = adjustment_score(score_margin, dominance_a, report_terms)
    if severity <= 0:
        return "normal", "", "", "normal_update", 0.0
    return (
        adj_type,
        loser_side(score_margin),
        winner_side(score_margin),
        "reduce_winner_reward_and_loser_penalty",
        severity,
    )


def confidence(severity: float, report_terms: str) -> str:
    context_bonus = 2.0 if report_terms else 0.0
    adjusted = severity + context_bonus
    if adjusted >= 18:
        return "high"
    if adjusted >= 11:
        return "medium"
    return "low"


def diff_note(a_stats: dict, b_stats: dict, perspective: str) -> str:
    parts = []
    sign = 1 if perspective == "A" else -1
    for key in NOTE_STATS:
        raw = stat(a_stats, key) - stat(b_stats, key)
        diff = raw * sign
        if abs(diff) < 0.01:
            continue
        # Keep the note compact by only showing meaningful edges.
        if key in {"run_metres", "post_contact_metres"} and abs(diff) < 80:
            continue
        if key in {"territory", "possession_percentage"} and abs(diff) < 5:
            continue
        if key not in {"run_metres", "post_contact_metres", "territory", "possession_percentage"} and abs(diff) < 3:
            continue
        parts.append(f"{key} {diff:+.1f}".replace(".0", ""))
    return "; ".join(parts[:9])


def build_rows(stats_dir: Path, reports_csv: Path, season: int, max_flags_per_round: int) -> list[dict]:
    reports = load_reports(reports_csv, season)
    rows = []
    by_round: dict[int, list[dict]] = defaultdict(list)

    for path in sorted(stats_dir.glob(f"NRL{season}*.json")):
        data = json.loads(path.read_text())
        match_id = data["match_id"]
        rnd = int(match_id[7:9])
        game = int(match_id[9:11])
        key = (season, rnd, game)

        team_a = data["team_A"]
        team_b = data["team_B"]
        a_name = canon_team(team_a["name"])
        b_name = canon_team(team_b["name"])
        a_stats = team_a["stats"]
        b_stats = team_b["stats"]
        a_points = int(stat(a_stats, "points"))
        b_points = int(stat(b_stats, "points"))
        score_margin = a_points - b_points
        dominance_a = stat_dominance(a_stats, b_stats)

        report_terms, report_titles, report_snippets = report_context(reports.get(key, []))
        adjustment_type, hard_side, lucky_side, action, severity = classify_candidate(
            score_margin, dominance_a, report_terms
        )

        winner = a_name if score_margin > 0 else (b_name if score_margin < 0 else "Draw")
        loser = b_name if score_margin > 0 else (a_name if score_margin < 0 else "Draw")
        hard_done_by = side_name(hard_side, a_name, b_name) if hard_side else ""
        lucky_winner = side_name(lucky_side, a_name, b_name) if lucky_side else ""

        perspective = hard_side or ("A" if dominance_a >= 0 else "B")
        notes = diff_note(a_stats, b_stats, perspective)
        if report_terms:
            notes = f"{notes}. Report context: {report_terms}" if notes else f"Report context: {report_terms}"

        row = {
            "season": season,
            "round": rnd,
            "game": game,
            "match_id": match_id,
            "match_date": reports.get(key, [{}])[0].get("match_date", ""),
            "team_a": a_name,
            "team_b": b_name,
            "score": f"{a_points}-{b_points}",
            "winner": winner,
            "loser": loser,
            "score_margin_a": score_margin,
            "stat_dominance_a": dominance_a,
            "mismatch_severity": round(severity, 2),
            "adjustment_type": adjustment_type,
            "stat_mismatch": "candidate" if severity else "no",
            "hard_done_by": hard_done_by,
            "lucky_winner": lucky_winner,
            "confidence": confidence(severity, report_terms) if severity else "low",
            "elo_v2_action": action,
            "report_context_terms": report_terms,
            "report_titles": report_titles,
            "notes": notes,
            "report_snippets": report_snippets,
        }
        rows.append(row)
        by_round[rnd].append(row)

    flagged = set()
    for rnd, round_rows in by_round.items():
        candidates = [r for r in round_rows if r["mismatch_severity"] >= 6.5]
        candidates.sort(key=lambda r: (-r["mismatch_severity"], r["game"]))
        round_flags = []
        for row in candidates:
            if not round_flags:
                round_flags.append(row)
            elif len(round_flags) < max_flags_per_round and row["mismatch_severity"] >= 9.0:
                round_flags.append(row)
        for row in round_flags:
            flagged.add(row["match_id"])

    for row in rows:
        if row["match_id"] in flagged:
            row["stat_mismatch"] = "yes"
        elif row["stat_mismatch"] == "candidate":
            row["stat_mismatch"] = "no_threshold"
            row["hard_done_by"] = ""
            row["lucky_winner"] = ""
            row["confidence"] = "low"
            row["elo_v2_action"] = "normal_update"
            row["adjustment_type"] = "normal"
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "season",
        "round",
        "game",
        "match_id",
        "match_date",
        "team_a",
        "team_b",
        "score",
        "winner",
        "loser",
        "score_margin_a",
        "stat_dominance_a",
        "mismatch_severity",
        "adjustment_type",
        "stat_mismatch",
        "hard_done_by",
        "lucky_winner",
        "confidence",
        "elo_v2_action",
        "report_context_terms",
        "report_titles",
        "notes",
        "report_snippets",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_review(rows: list[dict], path: Path, season: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = [r for r in rows if r["stat_mismatch"] == "yes"]
    high = [r for r in flags if r["confidence"] == "high"]
    medium = [r for r in flags if r["confidence"] == "medium"]
    low = [r for r in flags if r["confidence"] == "low"]
    type_counts = defaultdict(int)
    for row in flags:
        type_counts[row["adjustment_type"]] += 1

    lines = [
        f"# NRL Elo v2 Labels - {season} Season",
        "",
        "Generated from match stats first, with report snippets attached as context.",
        "",
        "## Summary",
        "",
        f"- Matches reviewed: {len(rows)}",
        f"- Elo v2 mismatch flags: {len(flags)}",
        f"- High confidence: {len(high)}",
        f"- Medium confidence: {len(medium)}",
        f"- Low confidence: {len(low)}",
        f"- Adjustment types: {', '.join(f'{key}={value}' for key, value in sorted(type_counts.items()))}",
        "- Default adjustment for flags: reduce winner reward and loser penalty",
        "- Starting experiment multipliers: 0.50 for stat reversal, 0.70 for margin exaggeration, 0.80 for close/report tension",
        "",
        "## Flagged Matches",
        "",
        "| Round | Match | Result | Type | Hard done by | Lucky winner | Conf | Severity | Notes |",
        "| ---: | --- | ---: | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in flags:
        match = f"{row['team_a']} vs {row['team_b']}"
        notes = row["notes"].replace("|", "/")
        lines.append(
            f"| {row['round']} | {match} | {row['score']} | {row['adjustment_type']} | {row['hard_done_by']} | "
            f"{row['lucky_winner']} | {row['confidence']} | {row['mismatch_severity']} | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Method",
            "",
            "A stat dominance score is calculated from score-independent match stats: line breaks, try assists, run metres, post-contact metres, tackle busts, opposition-20 tackles, forced dropouts, possession, territory, complete sets, errors, incomplete sets, penalties conceded, missed tackles and sin bins.",
            "",
            "A game is an adjustment candidate when the scoreboard winner is opposite to the stat dominance winner, when the margin looks inflated relative to the stat profile, or when a close result has weak winner support plus report context. Within each round, the top candidate is flagged above threshold and a second candidate is allowed when its score is also strong.",
            "",
            "Reports are not used to create the stat score. They only add context terms such as controversial, bunker, penalty try, sin bin, injury, HIA, no try, late, intercept, against the run of play or comeback.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NRL Elo v2 hard-done-by/lucky-winner labels")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--stats-dir", default=None)
    parser.add_argument("--reports-csv", default=str(ROOT / "outputs/nrl_game_reports/nrl_game_reports_2024_2025.csv"))
    parser.add_argument("--out-csv", default=None)
    parser.add_argument("--out-md", default=None)
    parser.add_argument("--max-flags-per-round", type=int, default=2)
    args = parser.parse_args()

    stats_dir = Path(args.stats_dir) if args.stats_dir else ROOT / f"ml/data/match_stats/{args.season}"
    out_csv = Path(args.out_csv) if args.out_csv else ROOT / f"outputs/nrl_elo_v2/season_{args.season}_labels.csv"
    out_md = Path(args.out_md) if args.out_md else ROOT / f"outputs/nrl_elo_v2/season_{args.season}_review.md"

    rows = build_rows(stats_dir, Path(args.reports_csv), args.season, args.max_flags_per_round)
    write_csv(rows, out_csv)
    write_review(rows, out_md, args.season)

    flags = [r for r in rows if r["stat_mismatch"] == "yes"]
    print(f"Reviewed {len(rows)} matches")
    print(f"Flagged {len(flags)} Elo v2 mismatch games")
    print(f"Wrote {out_csv}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
