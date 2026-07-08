"""
Add R14 NRL + R13 AFL bets to actual_bets_2026.csv and actual_bets_clv_2026.csv.
CLV formula: (odds_taken / close_odds - 1) * 100
Close odds sourced from CLV report (closes for matching game/market).
Run once only.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BETS_FILE = ROOT / "data/bets/actual_bets_2026.csv"
CLV_FILE  = ROOT / "data/clv/running/actual_bets_clv_2026.csv"

WEEK = "2026-06-08"

# ── Bet definitions ─────────────────────────────────────────────────────────
# Fields:
#   bet_id, placed_date, sport, season, round, home, away,
#   market_type, selection, line, odds_taken, stake, result,
#   bookmaker, notes,
#   close_odds, close_line, open_line
#
# close_odds = market close odds for the best-matching selection/line in CLV report
# close_line = closing line from CLV report (may differ from taken line)
# open_line  = line at time of bet (= line column)

BETS = [
    # ── NRL R14 ─────────────────────────────────────────────────────────────
    dict(
        bid="2026-0062", date="2026-06-05",
        sport="NRL", season=2026, rnd=14,
        home="Melbourne Storm", away="Newcastle Knights",
        market="handicap", sel="Newcastle Knights", line=4.5,
        odds=1.85, stake=25.0, result="win",
        book="sportsbet",
        notes="Newcastle +4.5 @ 1.85 | NRL R14",
        close_odds=1.90, close_line=2.5, open_line=4.5,
    ),
    dict(
        bid="2026-0063", date="2026-06-06",
        sport="NRL", season=2026, rnd=14,
        home="North Queensland Cowboys", away="Dolphins",
        market="h2h", sel="North Queensland Cowboys", line=None,
        odds=2.38, stake=20.0, result="loss",
        book="sportsbet",
        notes="Cowboys Win @ 2.38 | NRL R14",
        close_odds=2.65, close_line=None, open_line=None,  # estimated: Dolphins closed 1.52
    ),
    dict(
        bid="2026-0064", date="2026-06-06",
        sport="NRL", season=2026, rnd=14,
        home="Brisbane Broncos", away="Gold Coast Titans",
        market="total", sel="under", line=50.5,
        odds=1.90, stake=25.0, result="loss",
        book="sportsbet",
        notes="Under 50.5 @ 1.90 | NRL R14",
        close_odds=2.08, close_line=50.5, open_line=51.5,
    ),
    dict(
        bid="2026-0065", date="2026-06-07",
        sport="NRL", season=2026, rnd=14,
        home="Wests Tigers", away="Penrith Panthers",
        market="total", sel="under", line=49.5,
        odds=1.91, stake=25.0, result="loss",
        book="sportsbet",
        notes="Under 49.5 @ 1.91 | NRL R14",
        close_odds=2.20, close_line=49.5, open_line=49.5,
    ),
    dict(
        bid="2026-0066", date="2026-06-07",
        sport="NRL", season=2026, rnd=14,
        home="Cronulla-Sutherland Sharks", away="St. George Illawarra Dragons",
        market="handicap", sel="Cronulla-Sutherland Sharks", line=-10.5,
        odds=1.91, stake=20.0, result="win",
        book="sportsbet",
        notes="Cronulla -10.5 @ 1.91 | NRL R14",
        close_odds=1.90, close_line=-11.5, open_line=-12.5,
    ),
    dict(
        bid="2026-0067", date="2026-06-08",
        sport="NRL", season=2026, rnd=14,
        home="Canterbury-Bankstown Bulldogs", away="Parramatta Eels",
        market="handicap", sel="Canterbury-Bankstown Bulldogs", line=-5.5,
        odds=1.88, stake=25.0, result="loss",
        book="sportsbet",
        notes="Bulldogs -5.5 @ 1.88 | NRL R14",
        close_odds=1.85, close_line=-7.5, open_line=-3.5,
    ),
    dict(
        bid="2026-0068", date="2026-06-08",
        sport="NRL", season=2026, rnd=14,
        home="Canterbury-Bankstown Bulldogs", away="Parramatta Eels",
        market="handicap", sel="Canterbury-Bankstown Bulldogs", line=-6.5,
        odds=1.97, stake=20.0, result="loss",
        book="sportsbet",
        notes="Bulldogs -6.5 @ 1.97 | NRL R14",
        close_odds=1.85, close_line=-7.5, open_line=-3.5,
    ),

    # ── AFL R13 ─────────────────────────────────────────────────────────────
    dict(
        bid="2026-0069", date="2026-06-05",
        sport="AFL", season=2026, rnd=13,
        home="Hawthorn Hawks", away="Western Bulldogs",
        market="handicap", sel="Hawthorn Hawks", line=-11.5,
        odds=1.90, stake=25.0, result="loss",
        book="sportsbet",
        notes="Hawthorn -11.5 @ 1.90 | AFL R13 | Hawks lost",
        close_odds=1.95, close_line=-12.5, open_line=-22.5,
    ),
    dict(
        bid="2026-0070", date="2026-06-05",
        sport="AFL", season=2026, rnd=13,
        home="Hawthorn Hawks", away="Western Bulldogs",
        market="handicap", sel="Hawthorn Hawks", line=-20.5,
        odds=1.91, stake=20.0, result="loss",
        book="sportsbet",
        notes="Hawthorn -20.5 @ 1.91 | AFL R13 | line 8pts worse than close",
        close_odds=1.95, close_line=-12.5, open_line=-22.5,
    ),
    dict(
        bid="2026-0071", date="2026-06-05",
        sport="AFL", season=2026, rnd=13,
        home="Hawthorn Hawks", away="Western Bulldogs",
        market="handicap", sel="Hawthorn Hawks", line=-20.5,
        odds=1.91, stake=25.0, result="loss",
        book="sportsbet",
        notes="Hawthorn -20.5 @ 1.91 | AFL R13 stake 2",
        close_odds=1.95, close_line=-12.5, open_line=-22.5,
    ),
    dict(
        bid="2026-0072", date="2026-06-06",
        sport="AFL", season=2026, rnd=13,
        home="Gold Coast Suns", away="Brisbane Lions",
        market="total", sel="under", line=188.5,
        odds=1.88, stake=25.0, result="win",
        book="sportsbet",
        notes="Under 188.5 @ 1.88 | AFL R13 | actual 181",
        close_odds=2.04, close_line=186.5, open_line=188.5,
    ),
    dict(
        bid="2026-0073", date="2026-06-06",
        sport="AFL", season=2026, rnd=13,
        home="West Coast Eagles", away="Port Adelaide Power",
        market="handicap", sel="Port Adelaide Power", line=-6.5,
        odds=1.88, stake=30.0, result="loss",
        book="sportsbet",
        notes="Port -6.5 @ 1.88 | AFL R13 | exact close line",
        close_odds=1.90, close_line=-6.5, open_line=-10.5,
    ),
    dict(
        bid="2026-0074", date="2026-06-06",
        sport="AFL", season=2026, rnd=13,
        home="West Coast Eagles", away="Port Adelaide Power",
        market="handicap", sel="Port Adelaide Power", line=-7.5,
        odds=1.90, stake=25.0, result="loss",
        book="sportsbet",
        notes="Port -7.5 @ 1.90 | AFL R13 | 1pt worse than close",
        close_odds=1.90, close_line=-6.5, open_line=-10.5,
    ),
    dict(
        bid="2026-0075", date="2026-06-07",
        sport="AFL", season=2026, rnd=13,
        home="Sydney Swans", away="St Kilda Saints",
        market="handicap", sel="Sydney Swans", line=-29.5,
        odds=1.89, stake=25.0, result="loss",
        book="sportsbet",
        notes="Sydney -29.5 @ 1.89 | AFL R13 | close was -30.5",
        close_odds=1.95, close_line=-30.5, open_line=-28.5,
    ),
    dict(
        bid="2026-0076", date="2026-06-07",
        sport="AFL", season=2026, rnd=13,
        home="Essendon Bombers", away="Carlton Blues",
        market="total", sel="under", line=168.5,
        odds=1.89, stake=25.0, result="win",
        book="sportsbet",
        notes="Under 168.5 @ 1.89 | AFL R13 | exact close | actual 139",
        close_odds=2.00, close_line=168.5, open_line=173.5,
    ),
    dict(
        bid="2026-0077", date="2026-06-07",
        sport="AFL", season=2026, rnd=13,
        home="Essendon Bombers", away="Carlton Blues",
        market="total", sel="under", line=173.5,
        odds=1.88, stake=25.0, result="win",
        book="sportsbet",
        notes="Under 173.5 @ 1.88 | AFL R13 | 5pts better than close",
        close_odds=2.00, close_line=168.5, open_line=173.5,
    ),
    dict(
        bid="2026-0078", date="2026-06-08",
        sport="AFL", season=2026, rnd=13,
        home="Collingwood Magpies", away="Melbourne Demons",
        market="h2h", sel="Collingwood Magpies", line=None,
        odds=1.90, stake=20.0, result="loss",
        book="sportsbet",
        notes="Collingwood Win @ 1.90 | AFL R13 | Melbourne won",
        close_odds=1.90, close_line=None, open_line=None,
    ),
    dict(
        bid="2026-0079", date="2026-06-08",
        sport="AFL", season=2026, rnd=13,
        home="Collingwood Magpies", away="Melbourne Demons",
        market="h2h", sel="Collingwood Magpies", line=None,
        odds=1.90, stake=25.0, result="loss",
        book="sportsbet",
        notes="Collingwood Win @ 1.90 | AFL R13 stake 2",
        close_odds=1.90, close_line=None, open_line=None,
    ),
]


def pnl(b) -> float:
    if b["result"] == "win":
        return round((b["odds"] - 1) * b["stake"], 2)
    return -b["stake"]


def ret(b) -> float:
    if b["result"] == "win":
        return round(b["odds"] * b["stake"], 2)
    return 0.0


def clv_pct(b) -> float:
    return round((b["odds"] / b["close_odds"] - 1) * 100, 2)


def append_bets_ledger():
    rows = []
    for b in BETS:
        line_str = str(b["line"]) if b["line"] is not None else ""
        rows.append({
            "bet_id":           b["bid"],
            "week_ending":      WEEK,
            "placed_date":      b["date"],
            "placed_time":      "",
            "sport":            b["sport"],
            "season":           b["season"],
            "round":            b["rnd"],
            "home_team":        b["home"],
            "away_team":        b["away"],
            "market_type":      b["market"],
            "selection":        b["sel"],
            "line":             line_str,
            "odds_taken":       b["odds"],
            "stake":            b["stake"],
            "return_amount":    ret(b),
            "result":           b["result"],
            "pnl":              pnl(b),
            "bookmaker":        b["book"],
            "model_price":      "",
            "model_line":       "",
            "closing_price":    b["close_odds"],
            "closing_line":     str(b["close_line"]) if b["close_line"] is not None else "",
            "clv":              clv_pct(b),
            "source_signal_id": "",
            "source_text":      "",
            "notes":            b["notes"],
        })

    with open(BETS_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        for r in rows:
            w.writerow(r)
    print(f"  Appended {len(rows)} rows to {BETS_FILE.name}")


def append_clv_file():
    rows = []
    for b in BETS:
        home_last = b["home"].split()[-1]
        away_last  = b["away"].split()[-1]
        match_str  = f"{home_last} v {away_last}"
        line_str   = str(b["line"]) if b["line"] is not None else ""
        open_line_str  = str(b["open_line"])  if b["open_line"]  is not None else ""
        close_line_str = str(b["close_line"]) if b["close_line"] is not None else ""
        line_move = ""
        if b["open_line"] is not None and b["close_line"] is not None:
            line_move = round(b["close_line"] - b["open_line"], 1)

        rows.append({
            "bet_id":      b["bid"],
            "sport":       b["sport"],
            "round":       b["rnd"],
            "match":       match_str,
            "market":      b["market"],
            "selection":   b["sel"],
            "line":        line_str,
            "odds_taken":  b["odds"],
            "close_line":  close_line_str,
            "open_line":   open_line_str,
            "line_move":   line_move,
            "close_odds":  b["close_odds"],
            "clv_pct":     clv_pct(b),
            "clv_line":    "",
            "result":      b["result"],
            "pnl":         pnl(b),
        })

    with open(CLV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        for r in rows:
            w.writerow(r)
    print(f"  Appended {len(rows)} rows to {CLV_FILE.name}")


if __name__ == "__main__":
    # Safety check: verify last bet ID in ledger
    with open(BETS_FILE, newline="", encoding="utf-8-sig") as f:
        all_ids = [r["bet_id"] for r in csv.DictReader(f)]
    last_id = all_ids[-1]
    print(f"Last bet in ledger: {last_id}")
    if last_id != "2026-0061":
        print(f"ERROR: expected last bet 2026-0061, got {last_id}. Aborting — check before running.")
        raise SystemExit(1)

    append_bets_ledger()
    append_clv_file()
    print("Done.")
