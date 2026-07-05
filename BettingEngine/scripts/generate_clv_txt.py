"""
generate_clv_txt.py

Generates a formatted CLV review TXT from the weekly CLV report CSV.
Mirrors the format of results/clv_nrl_r8_2026.txt.

Usage:
  python generate_clv_txt.py --sport NRL --season 2026 --round 11
  python generate_clv_txt.py --sport AFL --season 2026 --round 10
"""
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def short(name: str) -> str:
    """Last word of team name for compact display."""
    parts = name.split()
    return parts[-1] if parts else name

def f(val, fmt=".1f"):
    try:
        return format(float(val), fmt)
    except (TypeError, ValueError):
        return "—"

def sign(val):
    try:
        v = float(val)
        return f"{v:+.1f}"
    except:
        return "—"

def pct(val):
    try:
        return f"{float(val)*100:+.1f}%"
    except:
        return "—"

def clv_h2h(model_fair, market_odds):
    """CLV = (1/model_fair) * market_odds - 1"""
    try:
        return (1.0 / float(model_fair)) * float(market_odds) - 1.0
    except:
        return None

def load_report(sport: str, season: int, rnd: int) -> list[dict]:
    sport_lower = sport.lower()
    path = ROOT / "outputs" / f"{sport_lower}_weekly_review" / "reports" / f"r{rnd}_{sport_lower}_clv_report_{season}.csv"
    if not path.exists():
        raise SystemExit(f"Report not found: {path}")
    with open(path, encoding="latin-1") as f:
        return list(csv.DictReader(f))


def group_rows(rows: list[dict]) -> dict:
    """Group by (home, away, market) -> {signal: row}"""
    games: dict[tuple, dict] = {}
    for r in rows:
        key = (r["home_team"], r["away_team"])
        games.setdefault(key, {"h2h": {}, "handicap": {}, "total": {}})
        mkt = r["market"]
        sig = r.get("signal", "normal")
        if mkt in games[key]:
            games[key][mkt][sig] = r
    return games


def handicap_pick_direction(model_margin, home_line_open) -> str:
    """Does model back HOME or AWAY to cover the market line?"""
    try:
        edge = float(model_margin) + float(home_line_open)
        return "HOME" if edge > 0 else "AWAY"
    except:
        return "?"


def market_move_direction(open_num, close_num) -> str:
    """HOME = market moved more toward home, AWAY = toward away."""
    try:
        move = float(close_num) - float(open_num)
        if abs(move) < 0.01:
            return "no_move"
        return "HOME" if move > 0 else "AWAY"
    except:
        return "?"


def generate(sport: str, season: int, rnd: int) -> str:
    rows = load_report(sport, season, rnd)
    games = group_rows(rows)

    lines = []
    W = 96

    def rule(char="="):
        lines.append(char * W)

    def h(txt):
        lines.append(txt)

    now = datetime.now().strftime("%Y-%m-%d")
    h(f"{sport} R{rnd} {season} — CLV Review")
    h(f"Model prices vs market (AusSportsBetting/OddsPortal)")
    h(f"Generated: {now}")
    rule()
    h("")
    h("METHODOLOGY")
    h("-----------")
    h("CLV (H2H) = (model_implied_prob × market_odds) - 1  where model_implied_prob = 1 / model_fair_odds")
    h("CLV (Handicap) = open_line - close_line  (positive = beat closing line)")
    h("CLV (Total)    = open_line - close_line  (positive = under moved your way)")
    h(f"Model prices from: outputs/{sport.lower()}_weekly_review/reports/r{rnd}_{sport.lower()}_clv_report_{season}.csv")
    h("")

    # ── H2H ──────────────────────────────────────────────────────────────────
    rule()
    h("H2H CLV")
    rule()
    h("")
    col = f"  {'Matchup':<32} {'Side':<6} {'Model Fair':>11} {'Mkt Open':>9} {'Mkt Close':>10} {'CLV@Open':>9} {'CLV@Close':>10}  {'Score':<9} Hit"
    h(col)
    h("  " + "─" * (W - 2))

    h2h_clvs_open = []
    h2h_clvs_close = []
    h2h_wins = 0
    h2h_total = 0

    for (home, away), mkts in games.items():
        r = mkts["h2h"].get("normal") or mkts["h2h"].get("model")
        if not r:
            continue

        hn, an = short(home), short(away)
        matchup = f"{hn} vs {an}"

        home_fair = r.get("model_home_fair_odds") or ""
        away_fair = r.get("model_away_fair_odds") or ""
        h_open    = r.get("open_odds") or ""
        h_close   = r.get("close_odds") or ""
        result    = r.get("result", "")

        # Which side does model favour? Lower fair odds = model favourite
        try:
            hf, af = float(home_fair), float(away_fair)
            if hf <= af:
                side = "HOME"
                model_fair = hf
                open_o = h_open
                close_o = h_close
                fav_name = home
            else:
                side = "AWAY"
                model_fair = af
                # Away odds from workbook — use same open/close (these are for model's selection)
                open_o  = h_open
                close_o = h_close
                fav_name = away
        except:
            side, model_fair, open_o, close_o, fav_name = "?", "", h_open, h_close, home

        clv_open  = clv_h2h(model_fair, open_o)
        clv_close = clv_h2h(model_fair, close_o)

        try:
            hs = int(float(r.get("home_score", 0)))
            as_ = int(float(r.get("away_score", 0)))
            score_str = f"{hs}-{as_}"
            winner = home if hs > as_ else (away if as_ > hs else "push")
            hit = "✓" if winner == fav_name else "✗"
            h2h_total += 1
            if winner == fav_name:
                h2h_wins += 1
        except:
            score_str, hit = "?", "?"

        clv_open_s  = f"{clv_open*100:+.1f}%"  if clv_open  is not None else "  —"
        clv_close_s = f"{clv_close*100:+.1f}%" if clv_close is not None else "  —"
        mf_s = f"{model_fair:.3f}" if model_fair else "  —"
        op_s = f"{float(open_o):.2f}"  if open_o  else "  —"
        cl_s = f"{float(close_o):.2f}" if close_o else "  —"

        if clv_open  is not None: h2h_clvs_open.append(clv_open * 100)
        if clv_close is not None: h2h_clvs_close.append(clv_close * 100)

        h(f"  {matchup:<32} {side:<6} {mf_s:>11} {op_s:>9} {cl_s:>10} {clv_open_s:>9} {clv_close_s:>10}  {score_str:<9} {hit}")

    avg_open  = sum(h2h_clvs_open)  / len(h2h_clvs_open)  if h2h_clvs_open  else None
    avg_close = sum(h2h_clvs_close) / len(h2h_clvs_close) if h2h_clvs_close else None
    h("")
    h(f"  Average CLV @ Open:  {avg_open:+.1f}%"  if avg_open  is not None else "  Average CLV @ Open:  —")
    h(f"  Average CLV @ Close: {avg_close:+.1f}%" if avg_close is not None else "  Average CLV @ Close: —")
    h(f"  H2H Results: {h2h_wins}/{h2h_total} ({h2h_wins/h2h_total*100:.0f}%)" if h2h_total else "  H2H Results: —")
    h("")
    h("  NOTE: Sample size is small. Need 200+ observations for reliable CLV averages.")
    h("")

    # ── HANDICAP ─────────────────────────────────────────────────────────────
    rule()
    h("HANDICAP")
    rule()
    h("")
    h(f"  {'Matchup':<32} {'Model':>8} {'Mkt Open':>9} {'Mkt Close':>10}  {'Mkt Direction':<20} {'Actual':>7}  Hit")
    h("  " + "─" * (W - 2))

    hcap_correct = 0
    hcap_total = 0
    toward_count = 0

    for (home, away), mkts in games.items():
        r = mkts["handicap"].get("normal") or mkts["handicap"].get("model")
        if not r:
            continue

        hn, an = short(home), short(away)
        matchup = f"{hn} vs {an}"

        mn   = r.get("model_number", "")
        on   = r.get("open_number", "")
        cn   = r.get("close_number", "")
        actual_margin = r.get("actual_margin_home", "")

        model_dir   = handicap_pick_direction(mn, on) if mn and on else "?"
        market_dir  = market_move_direction(on, cn)   if on and cn else "?"
        toward      = (market_dir != "no_move" and model_dir == market_dir)
        direction_s = f"{'TOWARD' if toward else 'AWAY'} ({market_dir})"
        if market_dir == "no_move":
            direction_s = "no_move"

        # Did model's direction call match outcome?
        try:
            am = float(actual_margin)  # positive = home won by X
            model_margin_f = float(mn)
            # model picks HOME if edge = model_margin + open_line > 0
            edge = model_margin_f + float(on)
            if abs(edge) < 0.01:
                hit = "—"
            elif edge > 0:
                # model backs home to cover
                cover_margin = float(on)  # home line (negative = home gives points)
                covered = am > -float(on)  # home won by more than they gave
                hit = "✓" if covered else "✗"
            else:
                # model backs away to cover
                cover_margin = -float(on)
                covered = am < -float(on)  # home won by less / away covered
                hit = "✓" if covered else "✗"

            if hit in ("✓", "✗"):
                hcap_total += 1
                if hit == "✓":
                    hcap_correct += 1
            if market_dir != "no_move":
                toward_count += (1 if toward else 0)
        except:
            hit = "?"

        line_move = ""
        try:
            move = float(cn) - float(on)
            line_move = f"{move:+.1f}"
        except:
            pass

        mn_s  = sign(mn)  if mn  else "  —"
        on_s  = sign(on)  if on  else "  —"
        cn_s  = sign(cn)  if cn  else "  —"
        am_s  = sign(actual_margin) if actual_margin else "  —"

        h(f"  {matchup:<32} {mn_s:>8} {on_s:>9} {cn_s:>10}  {direction_s:<20} {am_s:>7}  {hit}")

    h("")
    h(f"  Handicap correct: {hcap_correct}/{hcap_total} ({hcap_correct/hcap_total*100:.0f}%)" if hcap_total else "  Handicap correct: —")
    h(f"  Market moved toward model: {toward_count}/{hcap_total}" if hcap_total else "")
    h("")

    # ── TOTALS ────────────────────────────────────────────────────────────────
    rule()
    h("TOTALS")
    rule()
    h("")
    h(f"  {'Matchup':<32} {'Model':>8} {'Mkt Open':>9} {'Mkt Close':>10}  {'Gap':>6}  {'Actual':>7}  Hit")
    h("  " + "─" * (W - 2))

    tot_correct = 0
    tot_total = 0
    under_calls = 0

    for (home, away), mkts in games.items():
        r = mkts["total"].get("normal") or mkts["total"].get("model")
        if not r:
            continue

        hn, an = short(home), short(away)
        matchup = f"{hn} vs {an}"

        mn          = r.get("model_number", "")
        on          = r.get("open_number", "")
        cn          = r.get("close_number", "")
        actual_tot  = r.get("actual_total", "")

        try:
            gap = float(mn) - float(on)
            gap_s = f"{gap:+.1f}"
            # if model < market → under call
            direction = "UNDER" if gap < 0 else "OVER"
            if gap < 0:
                under_calls += 1
        except:
            gap_s, direction = "—", "?"

        try:
            at = float(actual_tot)
            market_line = float(on)
            if direction == "UNDER":
                hit = "✓ UNDER" if at < market_line else "✗ OVER  (miss)"
            else:
                hit = "✓ OVER"  if at > market_line else "✗ UNDER (miss)"
            tot_total += 1
            if hit.startswith("✓"):
                tot_correct += 1
        except:
            hit = "?"

        mn_s = f(mn) if mn else "  —"
        on_s = f(on) if on else "  —"
        cn_s = f(cn) if cn else "  —"
        at_s = f(actual_tot) if actual_tot else "  —"

        h(f"  {matchup:<32} {mn_s:>8} {on_s:>9} {cn_s:>10}  {gap_s:>6}  {at_s:>7}  {hit}")

    h("")
    h(f"  Under calls: {under_calls}/{tot_total} games model below market line")
    h(f"  Totals correct: {tot_correct}/{tot_total} ({tot_correct/tot_total*100:.0f}%)" if tot_total else "  Totals correct: —")
    h("")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    rule()
    h("SUMMARY")
    rule()
    h("")
    h(f"  H2H average CLV @ open:   {avg_open:+.1f}%  (elite benchmark: +3% sustained)" if avg_open is not None else "  H2H average CLV @ open:   —")
    h(f"  H2H average CLV @ close:  {avg_close:+.1f}%" if avg_close is not None else "  H2H average CLV @ close:  —")
    h(f"  H2H results:              {h2h_wins}/{h2h_total}     {h2h_wins/h2h_total*100:.0f}%" if h2h_total else "  H2H results: —")
    h(f"  Handicap correct:         {hcap_correct}/{hcap_total}     {hcap_correct/hcap_total*100:.0f}%" if hcap_total else "  Handicap correct: —")
    h(f"  Totals correct:           {tot_correct}/{tot_total}     {tot_correct/tot_total*100:.0f}%  ({under_calls}/{tot_total} under calls)" if tot_total else "  Totals correct: —")
    h("")
    h("  STATISTICAL CAVEAT:")
    h(f"  {len(games)} games. Not meaningful on its own. Target 200+ observations (~Round 15)")
    h("  before drawing conclusions on sustained CLV edge.")
    h("")
    rule()

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sport",  default="NRL", choices=["NRL", "AFL"])
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--round",  type=int, required=True, dest="rnd")
    p.add_argument("--out",    default=None, help="Output path (default: results/clv_{sport}_r{round}_{season}.txt)")
    args = p.parse_args()

    txt = generate(args.sport, args.season, args.rnd)

    out = Path(args.out) if args.out else ROOT / "results" / f"clv_{args.sport.lower()}_r{args.rnd}_{args.season}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nSaved to: {out}")


if __name__ == "__main__":
    main()
