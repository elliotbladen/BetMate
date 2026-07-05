# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests>=2.31",
#   "playwright>=1.40",
# ]
# ///
"""
scrapers/nrl_halftime_scraper.py

NRL half-time pipeline orchestrator.

1. Polls NRL draw API → detects games at half time (matchState="HalfTime")
2. For each half-time game → scrapes live stats from NRL.com match centre (Playwright)
3. Saves HalfTimeStats JSON → data/nrl/halfTime/R{nn}/
4. Auto-triggers halfTime_price_nrl.py

Usage:
    uv run python scrapers/nrl_halftime_scraper.py --round 14
    uv run python scrapers/nrl_halftime_scraper.py --round 14 --season 2026
    uv run python scrapers/nrl_halftime_scraper.py --round 14 --debug   # saves screenshots
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── Paths ─────────────────────────────────────────────────────────────────────
BETMATE_ROOT  = Path(os.environ.get("BETMATE_ROOT", Path(__file__).resolve().parent.parent))
SCRAPERS_DIR  = Path(__file__).resolve().parent
HALFTIME_DIR  = BETMATE_ROOT / "data" / "nrl" / "halfTime"
ENGINE_ROOT   = Path(os.environ.get("BETTING_ENGINE_ROOT", BETMATE_ROOT.parent / "Betting_model"))
SESSION_PATH  = HALFTIME_DIR / ".nrl_session.json"
ENV_PATH      = BETMATE_ROOT / ".env.local"
import shutil as _shutil
UV            = Path(os.environ.get("UV_PATH", _shutil.which("uv") or r"C:\Users\ElliotBladen\.local\bin\uv.exe"))

NRL_DRAW_API  = "https://www.nrl.com/draw/data/?competition=111&season={season}&round={round}"
NRL_BASE_URL  = "https://www.nrl.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,*/*",
}


# ── Env loader ────────────────────────────────────────────────────────────────

def load_env() -> dict[str, str]:
    """Load key=value pairs from .env.local."""
    env: dict[str, str] = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


# ── HalfTimeStats data model ──────────────────────────────────────────────────

@dataclass
class HalfTimeStats:
    season: int
    round: int
    game_date: str
    home_team: str
    away_team: str
    collected_at: str = ""
    source: str = "nrl_playwright"

    # Score
    home_ht_score: int = 0
    away_ht_score: int = 0

    # Key ETxP signal — tackles inside opponent's 20m
    home_inside_20_possessions: int = 0
    away_inside_20_possessions: int = 0

    # Ball security
    home_errors: int = 0
    away_errors: int = 0

    # Set restarts
    home_set_restarts_received: int = 0
    away_set_restarts_received: int = 0

    # Set completion
    home_completion_pct: float = 0.0
    away_completion_pct: float = 0.0

    # Conversions
    home_tries: int = 0
    away_tries: int = 0
    home_conversions_made: int = 0
    away_conversions_made: int = 0

    # Penalties
    home_penalties_conceded: int = 0
    away_penalties_conceded: int = 0

    # Run metres
    home_run_metres: int = 0
    away_run_metres: int = 0

    # Possession
    home_possession_pct: float = 0.0
    away_possession_pct: float = 0.0

    notes: str = ""


def save_stats(stats: HalfTimeStats) -> Path:
    stats.collected_at = datetime.now(timezone.utc).isoformat()
    round_dir = HALFTIME_DIR / f"R{stats.round:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    home_nick = stats.home_team.split()[-1].lower()
    away_nick = stats.away_team.split()[-1].lower()
    filename = f"{stats.game_date}_{home_nick}_vs_{away_nick}_stats.json"
    path = round_dir / filename
    path.write_text(json.dumps(asdict(stats), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Saved stats → {path}")
    return path


# ── NRL draw API ──────────────────────────────────────────────────────────────

def fetch_fixtures(season: int, round_num: int) -> list[dict]:
    url = NRL_DRAW_API.format(season=season, round=round_num)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [f for f in data.get("fixtures", []) if f.get("type") == "Match"]
    except Exception as exc:
        print(f"Draw API error: {exc}")
        return []


def is_halftime(fixture: dict) -> bool:
    """Check if a fixture is currently at half time."""
    state = (fixture.get("matchState") or "").lower()
    game_time = (fixture.get("clock") or {}).get("gameTime", "")

    # Explicit half time state
    if any(s in state for s in ("halftime", "half time", "half_time", "ht", "interval")):
        return True

    # Game clock at exactly 40:00 and match is live
    if game_time in ("40:00", "40") and "live" in state:
        return True

    return False


def get_fixture_info(fixture: dict) -> dict:
    """Extract key info from a fixture dict."""
    home = fixture.get("homeTeam", {})
    away = fixture.get("awayTeam", {})
    clock = fixture.get("clock", {})
    kickoff_str = clock.get("kickOffTimeLong", "")
    try:
        game_date = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        game_date = datetime.now().strftime("%Y-%m-%d")

    return {
        "home_team": home.get("nickName", ""),
        "away_team": away.get("nickName", ""),
        "home_score": int(home.get("score", 0) or 0),
        "away_score": int(away.get("score", 0) or 0),
        "match_centre_url": NRL_BASE_URL + fixture.get("matchCentreUrl", ""),
        "game_date": game_date,
        "game_time": clock.get("gameTime", ""),
        "match_state": fixture.get("matchState", ""),
    }


# ── Playwright scraper ────────────────────────────────────────────────────────

def scrape_match_stats(
    match_centre_url: str,
    credentials: dict[str, str],
    debug: bool = False,
) -> dict[str, dict[str, str]]:
    """
    Use Playwright to log in to NRL.com and scrape match centre stats.

    Returns dict: {"home": {stat_name: value}, "away": {stat_name: value}}
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    home_stats: dict[str, str] = {}
    away_stats: dict[str, str] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # Reuse saved session if available
        ctx_kwargs: dict = {"viewport": {"width": 1280, "height": 900}}
        if SESSION_PATH.exists():
            print("  Loading saved NRL session...")
            ctx_kwargs["storage_state"] = str(SESSION_PATH)

        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()

        try:
            # ── Login if no saved session ──────────────────────────────────
            if not SESSION_PATH.exists():
                print("  No saved session — logging in to NRL.com...")
                _login(page, credentials, debug)
                # Save session for next run
                SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(SESSION_PATH))
                print("  Session saved.")

            # ── Navigate to match centre ───────────────────────────────────
            print(f"  Navigating to: {match_centre_url}")
            page.goto(match_centre_url, wait_until="networkidle", timeout=30_000)

            if debug:
                page.screenshot(path=str(HALFTIME_DIR / "debug_matchcentre.png"))

            # ── Find and click the Stats tab ───────────────────────────────
            _click_stats_tab(page, debug)

            # ── Extract stats table ────────────────────────────────────────
            home_stats, away_stats = _extract_stats(page, debug)

        except PWTimeout as exc:
            print(f"  Playwright timeout: {exc}")
            if debug:
                page.screenshot(path=str(HALFTIME_DIR / "debug_timeout.png"))
        except Exception as exc:
            print(f"  Playwright error: {exc}")
            if debug:
                try:
                    page.screenshot(path=str(HALFTIME_DIR / "debug_error.png"))
                except Exception:
                    pass
        finally:
            browser.close()

    return {"home": home_stats, "away": away_stats}


def _login(page, credentials: dict[str, str], debug: bool) -> None:
    """Handle NRL.com Auth0 login flow."""
    from playwright.sync_api import TimeoutError as PWTimeout

    email    = credentials.get("NRL_EMAIL", "")
    password = credentials.get("NRL_PASSWORD", "")

    if not email or not password:
        raise ValueError("NRL_EMAIL and NRL_PASSWORD must be set in .env.local")

    # Go to NRL.com and trigger login
    page.goto("https://www.nrl.com", wait_until="domcontentloaded", timeout=20_000)

    # Try to find and click the login button
    login_selectors = [
        "a[href*='login']",
        "button:has-text('Log in')",
        "button:has-text('Sign in')",
        "[aria-label*='login']",
        "[data-testid*='login']",
    ]
    for sel in login_selectors:
        try:
            page.click(sel, timeout=3_000)
            break
        except Exception:
            continue
    else:
        # No login button found — try navigating directly
        page.goto("https://www.nrl.com/account/login", wait_until="domcontentloaded", timeout=20_000)

    if debug:
        page.screenshot(path=str(HALFTIME_DIR / "debug_login_page.png"))

    # Auth0 login form
    page.wait_for_selector("input[type='email'], input[name='email'], input[id*='email']", timeout=15_000)

    # Enter email
    email_sel = "input[type='email'], input[name='email'], input[id*='email']"
    page.fill(email_sel, email)

    # Some flows require clicking Continue/Next before showing password
    for continue_sel in ["button:has-text('Continue')", "button:has-text('Next')", "button[type='submit']"]:
        try:
            page.click(continue_sel, timeout=2_000)
            page.wait_for_timeout(1_000)
            break
        except Exception:
            continue

    # Enter password
    pw_sel = "input[type='password'], input[name='password'], input[id*='password']"
    page.wait_for_selector(pw_sel, timeout=10_000)
    page.fill(pw_sel, password)

    # Submit
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle", timeout=20_000)

    if debug:
        page.screenshot(path=str(HALFTIME_DIR / "debug_post_login.png"))

    print("  Login complete.")


def _click_stats_tab(page, debug: bool) -> None:
    """Find and click the Match Stats tab on the match centre page."""
    from playwright.sync_api import TimeoutError as PWTimeout

    stats_tab_selectors = [
        "button:has-text('Match Stats')",
        "button:has-text('Stats')",
        "a:has-text('Match Stats')",
        "a:has-text('Stats')",
        "[role='tab']:has-text('Stats')",
        "[data-tab='stats']",
        "[data-testid*='stats-tab']",
    ]

    for sel in stats_tab_selectors:
        try:
            page.click(sel, timeout=4_000)
            page.wait_for_load_state("networkidle", timeout=8_000)
            print("  Stats tab clicked.")
            if debug:
                page.screenshot(path=str(HALFTIME_DIR / "debug_stats_tab.png"))
            return
        except Exception:
            continue

    print("  WARNING: Could not find stats tab — parsing whatever is visible.")


def _extract_stats(page, debug: bool) -> tuple[dict[str, str], dict[str, str]]:
    """
    Extract home and away stats from the match centre stats table.

    NRL.com presents stats as rows: [stat label] [home value] [away value]
    We try multiple extraction strategies in order.
    """
    home: dict[str, str] = {}
    away: dict[str, str] = {}

    # Strategy 1: Look for stat rows by common class patterns
    try:
        rows = page.query_selector_all(
            "[class*='stat-row'], [class*='match-stat'], "
            "[class*='team-stat'], [class*='statRow'], "
            "[class*='matchStat']"
        )
        if rows:
            for row in rows:
                text = row.inner_text().strip()
                parts = [p.strip() for p in text.split("\n") if p.strip()]
                if len(parts) >= 3:
                    label = parts[0]
                    home[label] = parts[1]
                    away[label] = parts[-1]
            if home:
                print(f"  Strategy 1 (class pattern): {len(home)} stats found.")
                return home, away
    except Exception:
        pass

    # Strategy 2: Table rows
    try:
        rows = page.query_selector_all("tr")
        for row in rows:
            cells = row.query_selector_all("td, th")
            if len(cells) >= 3:
                label = cells[0].inner_text().strip()
                home_val = cells[1].inner_text().strip()
                away_val = cells[-1].inner_text().strip()
                if label and home_val:
                    home[label] = home_val
                    away[label] = away_val
        if home:
            print(f"  Strategy 2 (table rows): {len(home)} stats found.")
            return home, away
    except Exception:
        pass

    # Strategy 3: dl/dt/dd definition lists
    try:
        items = page.query_selector_all("dl, [class*='definition']")
        for item in items:
            text = item.inner_text().strip()
            parts = [p.strip() for p in text.split("\n") if p.strip()]
            if len(parts) >= 3:
                label = parts[0]
                home[label] = parts[1]
                away[label] = parts[-1]
        if home:
            print(f"  Strategy 3 (definition lists): {len(home)} stats found.")
            return home, away
    except Exception:
        pass

    # Strategy 4: Full page text parsing (last resort)
    try:
        content = page.inner_text("body")
        print(f"  Strategy 4 (text parse): parsing {len(content)} chars of page text.")
        if debug:
            (HALFTIME_DIR / "debug_page_text.txt").write_text(content, encoding="utf-8")
        # Minimal parse — at least return empty so caller knows to check debug file
    except Exception:
        pass

    print("  WARNING: Could not extract stats. Run with --debug to save page screenshots.")
    return home, away


# ── Stat field mapper ─────────────────────────────────────────────────────────

# NRL.com stat label → HalfTimeStats field mapping
# Multiple label variants in case NRL.com changes naming
STAT_MAP: dict[str, tuple[str, str]] = {
    # label (lowercase)            : (home_field, away_field)
    "tries":                        ("home_tries",                  "away_tries"),
    "conversions":                  ("home_conversions_made",        "away_conversions_made"),
    "conversion goals":             ("home_conversions_made",        "away_conversions_made"),
    "errors":                       ("home_errors",                  "away_errors"),
    "handling errors":              ("home_errors",                  "away_errors"),
    "run metres":                   ("home_run_metres",              "away_run_metres"),
    "running metres":               ("home_run_metres",              "away_run_metres"),
    "metres":                       ("home_run_metres",              "away_run_metres"),
    "set completions":              ("home_completion_pct",          "away_completion_pct"),
    "set completion %":             ("home_completion_pct",          "away_completion_pct"),
    "completion rate":              ("home_completion_pct",          "away_completion_pct"),
    "completion %":                 ("home_completion_pct",          "away_completion_pct"),
    "set restarts":                 ("home_set_restarts_received",   "away_set_restarts_received"),
    "6 agains":                     ("home_set_restarts_received",   "away_set_restarts_received"),
    "six agains":                   ("home_set_restarts_received",   "away_set_restarts_received"),
    "six again":                    ("home_set_restarts_received",   "away_set_restarts_received"),
    "tackle breaks":                ("home_set_restarts_received",   "away_set_restarts_received"),  # fallback if no restart label
    "tackles inside 20":            ("home_inside_20_possessions",   "away_inside_20_possessions"),
    "tackles inside 20m":           ("home_inside_20_possessions",   "away_inside_20_possessions"),
    "inside 20":                    ("home_inside_20_possessions",   "away_inside_20_possessions"),
    "inside 20m":                   ("home_inside_20_possessions",   "away_inside_20_possessions"),
    "20m tackles":                  ("home_inside_20_possessions",   "away_inside_20_possessions"),
    "penalties":                    ("home_penalties_conceded",      "away_penalties_conceded"),
    "penalties conceded":           ("home_penalties_conceded",      "away_penalties_conceded"),
    "possession":                   ("home_possession_pct",          "away_possession_pct"),
    "possession %":                 ("home_possession_pct",          "away_possession_pct"),
}


def _parse_num(val: str, is_pct: bool = False) -> float:
    """Parse a stat value string to float. Handles '78%', '1,234', etc."""
    val = val.strip().replace(",", "").replace("%", "").strip()
    try:
        return float(val)
    except ValueError:
        return 0.0


def map_stats(
    raw: dict[str, dict[str, str]],
    home_team: str,
    away_team: str,
    season: int,
    round_num: int,
    game_date: str,
    home_score: int,
    away_score: int,
) -> HalfTimeStats:
    """Map raw scraped stats dict → HalfTimeStats dataclass."""
    stats = HalfTimeStats(
        season=season,
        round=round_num,
        game_date=game_date,
        home_team=home_team,
        away_team=away_team,
        home_ht_score=home_score,
        away_ht_score=away_score,
    )

    home_raw = raw.get("home", {})
    away_raw = raw.get("away", {})

    # Log all discovered stat labels for field name investigation
    if home_raw:
        print(f"  Discovered stat labels: {list(home_raw.keys())}")

    for label, (home_field, away_field) in STAT_MAP.items():
        # Try exact match then case-insensitive
        h_val = home_raw.get(label) or next(
            (v for k, v in home_raw.items() if k.lower() == label), None
        )
        a_val = away_raw.get(label) or next(
            (v for k, v in away_raw.items() if k.lower() == label), None
        )

        if h_val is not None:
            is_pct = "pct" in home_field
            setattr(stats, home_field, _parse_num(h_val, is_pct))
        if a_val is not None:
            is_pct = "pct" in away_field
            setattr(stats, away_field, _parse_num(a_val, is_pct))

    # Convert float fields that should be int
    for int_field in (
        "home_tries", "away_tries",
        "home_conversions_made", "away_conversions_made",
        "home_errors", "away_errors",
        "home_set_restarts_received", "away_set_restarts_received",
        "home_inside_20_possessions", "away_inside_20_possessions",
        "home_penalties_conceded", "away_penalties_conceded",
        "home_run_metres", "away_run_metres",
    ):
        setattr(stats, int_field, int(getattr(stats, int_field, 0)))

    return stats


# ── Pricing trigger ───────────────────────────────────────────────────────────

def trigger_pricing(stats_path: Path) -> None:
    """Auto-trigger halfTime_price_nrl.py after stats are collected."""
    pricing_script = ENGINE_ROOT / "scripts" / "halfTime_price_nrl.py"
    if not pricing_script.exists():
        print(f"  Pricing script not found: {pricing_script}")
        return

    cmd = [str(UV), "run", "python", str(pricing_script),
           "--file", str(stats_path), "--save"]
    try:
        result = subprocess.run(cmd, capture_output=False, timeout=30)
        if result.returncode != 0:
            print("  Pricing model returned non-zero exit code.")
    except Exception as exc:
        print(f"  Could not trigger pricing: {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NRL half-time scraper")
    p.add_argument("--round",   type=int, required=True)
    p.add_argument("--season",  type=int, default=datetime.now().year)
    p.add_argument("--debug",   action="store_true", help="Save screenshots + page text")
    p.add_argument("--force",   action="store_true", help="Scrape even if game not at half time (testing)")
    p.add_argument("--clear-session", action="store_true", help="Delete saved session and re-login")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.clear_session and SESSION_PATH.exists():
        SESSION_PATH.unlink()
        print("Cleared saved NRL session.")

    env = load_env()
    if not env.get("NRL_EMAIL") or not env.get("NRL_PASSWORD"):
        print("ERROR: NRL_EMAIL and NRL_PASSWORD not found in .env.local")
        sys.exit(1)

    print(f"\nFetching NRL draw — R{args.round} {args.season}...")
    fixtures = fetch_fixtures(args.season, args.round)
    print(f"Found {len(fixtures)} fixtures.")

    halftime_fixtures = [f for f in fixtures if is_halftime(f) or args.force]

    if not halftime_fixtures:
        print("No games at half time.")
        if fixtures:
            states = [(f.get("homeTeam", {}).get("nickName"), f.get("matchState")) for f in fixtures]
            print(f"Current states: {states}")
        return

    for fixture in halftime_fixtures:
        info = get_fixture_info(fixture)
        print(f"\n{'='*60}")
        print(f"HALF TIME: {info['home_team']} {info['home_score']} – "
              f"{info['away_score']} {info['away_team']}")
        print(f"  Match centre: {info['match_centre_url']}")
        print(f"{'='*60}")

        print("\n  Scraping match centre stats...")
        raw = scrape_match_stats(
            match_centre_url=info["match_centre_url"],
            credentials=env,
            debug=args.debug,
        )

        stats = map_stats(
            raw=raw,
            home_team=info["home_team"],
            away_team=info["away_team"],
            season=args.season,
            round_num=args.round,
            game_date=info["game_date"],
            home_score=info["home_score"],
            away_score=info["away_score"],
        )

        stats_path = save_stats(stats)

        print("\n  Triggering pricing model...")
        trigger_pricing(stats_path)

    print(f"\nDone — processed {len(halftime_fixtures)} half-time game(s).")


if __name__ == "__main__":
    main()
