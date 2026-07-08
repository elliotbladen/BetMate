"""
Scrape Rugby League Project game-by-game data for the 7 primary NRL referees.
Loads NRL Premiership games 2022-2026 into model.db referee_game_stats table.
"""
import sqlite3
import time
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

REFS = [
    ("Ashley Klein",   "ashley-klein-ref"),
    ("Gerard Sutton",  "gerard-sutton-ref"),
    ("Grant Atkins",   "grant-atkins-ref"),
    ("Adam Gee",       "adam-gee-ref"),
    ("Todd Smith",     "todd-smith-ref"),
    ("Peter Gough",    "peter-gough-ref"),
    ("Wyatt Raymond",  "wyatt-raymond-ref"),
]

BASE_URL = "https://www.rugbyleagueproject.org/referees/{slug}/games.html"
DB_PATH  = Path("data/model.db")
MONTHS   = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
            "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def clean(s):
    return s.replace("\xa0", "").strip()


def parse_score_pair(s):
    """'52 - 4'  →  (52, 4)   or (None, None)"""
    s = clean(s)
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def parse_games(html, ref_name):
    soup  = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        print(f"  WARNING: no table found for {ref_name}")
        return []

    rows = table.find_all("tr")
    headers = [th.get_text(strip=True) for th in rows[0].find_all("th")] if rows else []

    # Column index map (tolerate minor variations)
    idx = {h.lower(): i for i, h in enumerate(headers)}

    games = []
    current_year  = None
    current_month = None

    for row in rows[1:]:
        cells = [clean(td.get_text(" ", strip=True)) for td in row.find_all("td")]
        if len(cells) < 7:
            continue

        # ── Year ──────────────────────────────────────────────────────────
        year_val = cells[idx.get("year", 0)]
        if re.match(r"^\d{4}$", year_val):
            current_year = int(year_val)

        if current_year is None or current_year < 2022:
            continue                         # skip all pre-2022 rows
        if current_year > 2026:
            continue

        # ── Competition filter ─────────────────────────────────────────────
        comp = cells[idx.get("competition", 2)]
        if "NRL Premiership" not in comp:
            continue                         # skip NRLW, Super League, Intl etc.

        # ── Role filter ────────────────────────────────────────────────────
        role_idx = idx.get("role", len(cells) - 2)
        role = cells[role_idx] if role_idx < len(cells) else ""
        if "Referee" not in role:
            continue                         # skip Touch Judge, Video Ref rows

        # ── Date (reconstruct month) ───────────────────────────────────────
        date_val = cells[idx.get("date", 1)]
        m_match  = re.match(r"([A-Z][a-z]{2})\s+(\d+)", date_val)
        if m_match:
            current_month = MONTHS.get(m_match.group(1))
            day           = int(m_match.group(2))
        elif re.match(r"^\d{1,2}$", date_val):
            day = int(date_val)
        else:
            day = None

        date_str = (f"{current_year}-{current_month:02d}-{day:02d}"
                    if current_month and day else f"{current_year}")

        # ── Score ──────────────────────────────────────────────────────────
        score_raw = cells[idx.get("score", 5)]
        home_score, away_score = parse_score_pair(score_raw)
        if home_score is None:
            continue                         # future game or bad data

        total_score = home_score + away_score

        # ── Penalties ─────────────────────────────────────────────────────
        pen_raw = cells[idx.get("penalties", 8)]
        home_pen, away_pen = parse_score_pair(pen_raw)
        total_pen = (home_pen + away_pen) if home_pen is not None else None

        # ── Other fields ──────────────────────────────────────────────────
        round_label = cells[idx.get("round", 3)]
        home_team   = cells[idx.get("home", 4)]
        away_team   = cells[idx.get("away", 6)]
        venue       = cells[idx.get("venue", 9)] if len(cells) > 9 else ""
        crowd_raw   = cells[idx.get("crowd", 10)] if len(cells) > 10 else ""
        try:
            crowd = int(crowd_raw.replace(",", "").replace(".", ""))
        except (ValueError, AttributeError):
            crowd = None

        games.append({
            "referee_name":   ref_name,
            "season":         current_year,
            "date_str":       date_str,
            "competition":    comp,
            "round_label":    round_label,
            "home_team":      home_team,
            "home_score":     home_score,
            "away_score":     away_score,
            "total_score":    total_score,
            "home_penalties": home_pen,
            "away_penalties": away_pen,
            "total_penalties":total_pen,
            "venue":          venue,
            "crowd":          crowd,
        })

    return games


def setup_db(conn):
    conn.executescript("""
        DROP TABLE IF EXISTS referee_game_stats;

        CREATE TABLE referee_game_stats (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            referee_name     TEXT    NOT NULL,
            season           INTEGER NOT NULL,
            date_str         TEXT,
            competition      TEXT,
            round_label      TEXT,
            home_team        TEXT,
            home_score       INTEGER,
            away_score       INTEGER,
            total_score      INTEGER,
            home_penalties   INTEGER,
            away_penalties   INTEGER,
            total_penalties  INTEGER,
            venue            TEXT,
            crowd            INTEGER,
            scraped_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_rgs_ref_season
            ON referee_game_stats(referee_name, season);
    """)
    conn.commit()


def insert_games(conn, games):
    conn.executemany("""
        INSERT INTO referee_game_stats
            (referee_name, season, date_str, competition, round_label,
             home_team, home_score, away_score, total_score,
             home_penalties, away_penalties, total_penalties, venue, crowd)
        VALUES
            (:referee_name, :season, :date_str, :competition, :round_label,
             :home_team, :home_score, :away_score, :total_score,
             :home_penalties, :away_penalties, :total_penalties, :venue, :crowd)
    """, games)
    conn.commit()


def print_summary(conn):
    print("\n" + "=" * 80)
    print("  NRL REFEREE STATS — 2022-2026  |  NRL Premiership games only")
    print("=" * 80)

    # Overall per referee
    print(f"\n  {'Referee':<26} {'Games':>6} {'Avg Total':>10} {'Avg Pen':>9} {'Min':>5} {'Max':>5} {'<45':>6} {'<48':>6}")
    print(f"  {'-'*72}")

    rows = conn.execute("""
        SELECT referee_name,
               COUNT(*)                           AS games,
               ROUND(AVG(total_score), 1)         AS avg_total,
               ROUND(AVG(total_penalties), 1)     AS avg_pen,
               MIN(total_score)                   AS min_score,
               MAX(total_score)                   AS max_score,
               SUM(CASE WHEN total_score < 45 THEN 1 ELSE 0 END) AS under45,
               SUM(CASE WHEN total_score < 48 THEN 1 ELSE 0 END) AS under48
        FROM referee_game_stats
        GROUP BY referee_name
        ORDER BY avg_total
    """).fetchall()

    league_totals = [r[2] for r in rows]
    league_avg    = sum(r[1] * r[2] for r in rows) / sum(r[1] for r in rows)

    for r in rows:
        delta = r[2] - league_avg
        sign  = "▲" if delta >= 0.5 else ("▼" if delta <= -0.5 else " ")
        u45_pct = f"{r[6]/r[1]*100:.0f}%"
        u48_pct = f"{r[7]/r[1]*100:.0f}%"
        print(f"  {r[0]:<26} {r[1]:>6} {r[2]:>9.1f}{sign} {r[3]:>9.1f} {r[4]:>5} {r[5]:>5} {u45_pct:>6} {u48_pct:>6}")

    print(f"\n  League average (weighted): {league_avg:.1f} pts")

    # Per-season breakdown
    print(f"\n\n  PER-SEASON AVERAGE TOTAL")
    print(f"  {'Referee':<26} {'2022':>7} {'2023':>7} {'2024':>7} {'2025':>7} {'2026':>7}")
    print(f"  {'-'*60}")

    ref_names = [r[0] for r in rows]
    for ref in ref_names:
        row_parts = [f"  {ref:<26}"]
        for yr in [2022, 2023, 2024, 2025, 2026]:
            val = conn.execute("""
                SELECT ROUND(AVG(total_score),1), COUNT(*)
                FROM referee_game_stats
                WHERE referee_name=? AND season=?
            """, (ref, yr)).fetchone()
            if val and val[1] > 0:
                row_parts.append(f"{val[0]:>7.1f}")
            else:
                row_parts.append(f"{'—':>7}")
        print("".join(row_parts))

    # Delta vs league average (key for T6)
    print(f"\n\n  T6 ADJUSTMENT TABLE  (ref avg - league avg = pts delta on totals)")
    print(f"  League avg (2022-2026): {league_avg:.1f}")
    print(f"\n  {'Referee':<26} {'Ref Avg':>8} {'Delta':>8} {'Adj':>8} {'Style':<15}")
    print(f"  {'-'*65}")

    for r in rows:
        delta    = r[2] - league_avg
        adj      = round(delta / 2, 1)   # conservative: take half the delta
        style    = "HIGH SCORING" if delta > 2 else ("LOW SCORING" if delta < -2 else "NEUTRAL")
        print(f"  {r[0]:<26} {r[2]:>8.1f} {delta:>+8.1f} {adj:>+8.1f} {style:<15}")

    print(f"\n  NOTE: Adj is delta/2 — conservative dampener to avoid over-fitting to sample.")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)

    all_games = []
    for ref_name, slug in REFS:
        url = BASE_URL.format(slug=slug)
        print(f"Fetching {ref_name} → {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            games = parse_games(resp.text, ref_name)
            print(f"  → {len(games)} NRL Premiership games (2022-2026) parsed")
            all_games.extend(games)
            insert_games(conn, games)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(1.5)   # polite delay

    print(f"\nTotal rows inserted: {len(all_games)}")
    print_summary(conn)
    conn.close()
