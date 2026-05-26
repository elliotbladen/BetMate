"""
lib/scraper/nrl_emotional.py

Generates T7 emotional flags for the upcoming NRL round.

Data sources (all read from BetMate's own processed files):
  - data/nrl/news_flags/processed/latest.json    — injuries, suspensions, team news
  - data/nrl/injuries/processed/latest-injuries.json — T5 injury list (star_return diff)
  - data/nrl/fixture/processed/latest-fixture.json  — upcoming round fixture
  - BettingEngine DB (optional, --db-path) — previous round results for shame_blowout

Deterministic detections (no AI needed):
  - shame_blowout:    lost by 30+ last round (from DB results or news_flags context)
  - rivalry_derby:    fixture vs known rivalry pair
  - origin_boost:     round falls in post-Origin camp window (configurable dates)

Baz / Claude layer (Anthropic API):
  - Reviews all data, adds: milestone, star_return, must_win, new_coach, farewell
  - Returns structured JSON matching load_emotional_round.py format

Output:
  data/nrl/emotional/raw/YYYY/round-N.json          (raw API response)
  data/nrl/emotional/processed/YYYY/round-N.json    (validated flags)
  data/nrl/emotional/processed/latest-emotional.json (consumed by BettingEngine)
  data/nrl/emotional/logs/scrape.log

Usage:
  uv run --with anthropic --with requests python lib/scraper/nrl_emotional.py --round 11
  uv run --with anthropic --with requests python lib/scraper/nrl_emotional.py --round 11 --db-path C:/path/to/model.db
  uv run --with anthropic --with requests python lib/scraper/nrl_emotional.py --round 11 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT      = Path(__file__).resolve().parents[1]
BASE_DIR  = ROOT / "data" / "nrl" / "emotional"
RAW_DIR   = BASE_DIR / "raw"
PROC_DIR  = BASE_DIR / "processed"
LOG_DIR   = BASE_DIR / "logs"
LOG_PATH  = LOG_DIR / "scrape.log"

VALID_FLAG_TYPES = {
    'milestone', 'new_coach', 'star_return', 'shame_blowout',
    'origin_boost', 'farewell', 'personal_tragedy', 'rivalry_derby', 'must_win',
}
VALID_STRENGTHS = {'minor', 'normal', 'major'}

SHAME_BLOWOUT_THRESHOLD = 30

# Known NRL rivalries — both orderings are checked
RIVALRIES: list[frozenset[str]] = [
    frozenset({'South Sydney Rabbitohs', 'Sydney Roosters'}),
    frozenset({'South Sydney Rabbitohs', 'St. George Illawarra Dragons'}),
    frozenset({'Wests Tigers', 'South Sydney Rabbitohs'}),
    frozenset({'Wests Tigers', 'Sydney Roosters'}),
    frozenset({'Wests Tigers', 'Parramatta Eels'}),
    frozenset({'Parramatta Eels', 'Canterbury-Bankstown Bulldogs'}),
    frozenset({'Brisbane Broncos', 'North Queensland Cowboys'}),
    frozenset({'Brisbane Broncos', 'Sydney Roosters'}),
    frozenset({'Manly-Warringah Sea Eagles', 'Sydney Roosters'}),
    frozenset({'Penrith Panthers', 'Parramatta Eels'}),
    frozenset({'Newcastle Knights', 'Canberra Raiders'}),
    frozenset({'St. George Illawarra Dragons', 'Cronulla-Sutherland Sharks'}),
    frozenset({'Melbourne Storm', 'Sydney Roosters'}),
    frozenset({'Gold Coast Titans', 'Brisbane Broncos'}),
    frozenset({'New Zealand Warriors', 'Brisbane Broncos'}),
]

# Post-Origin camp boost windows (AEST dates, inclusive).
# State of Origin typically runs May-July. Teams get a lift the round
# after their players return. Update each season.
ORIGIN_BOOST_WINDOWS_2026: list[tuple[str, str, str]] = [
    # (first_round_after_camp, last_round_after_camp, notes)
    # Game 1 ~June 4, players back for round ~15-16
    ('2026-06-05', '2026-06-14', 'Post-Origin Game 1 camp window'),
    ('2026-07-02', '2026-07-12', 'Post-Origin Game 2 camp window'),
    ('2026-07-23', '2026-08-02', 'Post-Origin Game 3 camp window'),
]

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the NRL emotional context analyst for a sports pricing engine.

Your job is to identify MEANINGFUL emotional/motivational storylines that will materially
affect a team's performance in the upcoming round. You are conservative — most games have
no emotional flags. Expect 0–2 per round total.

You will receive:
1. The upcoming round fixture
2. Previous round results (if available)
3. Current injury/suspension/news flags from BetMate
4. Auto-detected flags (shame_blowout, rivalry_derby, origin_boost) already confirmed

Your task: identify any ADDITIONAL flags from these types only:
  milestone        — 100th/150th/200th/250th/300th NRL game, debut, first game as captain
  new_coach        — first game under a newly appointed head coach
  star_return      — elite/key player returning from 3+ weeks injured
  farewell         — confirmed retirement game, player's last season announcement
  personal_tragedy — team rallying around a recent death, serious illness, family tragedy
  must_win         — team mathematically or effectively eliminated without a win, OR
                     team in last 4 of ladder with ≤6 rounds left and on a 3+ game losing streak

For each flag you identify, return a JSON object:
  {
    "season": <int>,
    "round": <int>,
    "team": "<full team name>",
    "flag_type": "<one of the valid types>",
    "flag_strength": "<minor|normal|major>",
    "player_name": "<name or null>",
    "notes": "<1-2 sentence explanation>",
    "confidence": "<high|medium|low>"
  }

Return a JSON array. Return [] if no additional flags apply.
Only include flags you are CONFIDENT about. Do not speculate.
Do not repeat flags already in the auto-detected list.
Use full canonical NRL team names (e.g. "Cronulla-Sutherland Sharks" not "Sharks").
"""


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(LOG_PATH, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def load_json(path: Path) -> list | dict | None:
    if not path.exists():
        log.warning('File not found: %s', path)
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        log.warning('Failed to parse %s: %s', path, exc)
        return None


def detect_shame_blowout(db_path: str | None, prev_round: int, season: int) -> list[dict]:
    """Query BettingEngine DB for teams that lost by SHAME_BLOWOUT_THRESHOLD+ last round."""
    if not db_path or not Path(db_path).exists():
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT h.team_name AS home, a.team_name AS away,
                   r.home_score, r.away_score,
                   ABS(r.home_score - r.away_score) AS margin
            FROM   results r
            JOIN   matches m  ON m.match_id     = r.match_id
            JOIN   teams   h  ON h.team_id      = m.home_team_id
            JOIN   teams   a  ON a.team_id      = m.away_team_id
            WHERE  m.season = ? AND m.round_number = ?
              AND  r.result_status = 'final'
            """,
            (season, prev_round),
        ).fetchall()
        conn.close()
    except Exception as exc:
        log.warning('DB query failed for shame_blowout: %s', exc)
        return []

    flags = []
    for r in rows:
        margin = r['margin']
        if margin < SHAME_BLOWOUT_THRESHOLD:
            continue
        if r['home_score'] < r['away_score']:
            loser = r['home']
        else:
            loser = r['away']
        strength = 'major' if margin >= 40 else 'normal'
        flags.append({
            'flag_type':     'shame_blowout',
            'flag_strength': strength,
            'team':          loser,
            'player_name':   None,
            'notes':         (
                f"Lost by {margin} points in R{prev_round} "
                f"({r['home']} {r['home_score']}-{r['away_score']} {r['away']}). "
                f"Classic bounce-back situation."
            ),
            'source': 'db_results',
        })
        log.info('shame_blowout detected: %s (margin=%d)', loser, margin)

    return flags


def detect_rivalry_derby(fixture: list[dict], season: int, round_number: int) -> list[dict]:
    """Check each game against known rivalry pairs."""
    flags = []
    for game in fixture:
        home = game.get('home_team', '')
        away = game.get('away_team', '')
        pair = frozenset({home, away})
        if pair in RIVALRIES:
            flags.append({
                'flag_type':     'rivalry_derby',
                'flag_strength': 'normal',
                'team':          home,
                'player_name':   None,
                'notes':         f'{home} vs {away} is a recognised NRL rivalry fixture.',
                'source':        'fixture_rivalry',
            })
            log.info('rivalry_derby detected: %s vs %s', home, away)
    return flags


def detect_origin_boost(fixture: list[dict], season: int, round_number: int) -> list[dict]:
    """Flag teams in the round after Origin camp windows."""
    if season != 2026:
        return []

    # Get the earliest kickoff date in the fixture to check windows
    kickoffs = [g.get('kickoff_local', '') or g.get('kickoff_utc', '') for g in fixture]
    kickoffs = [k[:10] for k in kickoffs if k]
    if not kickoffs:
        return []

    round_date = min(kickoffs)

    for window_start, window_end, notes in ORIGIN_BOOST_WINDOWS_2026:
        if window_start <= round_date <= window_end:
            log.info('origin_boost window active for R%d (%s): %s', round_number, round_date, notes)
            # Flag all teams — Origin affects multiple clubs
            # A generic flag per team is too noisy; flag it at the round level with no specific team
            # We'll return a sentinel that the caller can attach per-game or skip
            return [{'_origin_window': notes, '_round_date': round_date}]

    return []


def build_claude_prompt(
    season: int,
    round_number: int,
    fixture: list[dict],
    prev_results: list[dict],
    news_flags: list[dict],
    auto_flags: list[dict],
) -> str:
    fixture_lines = '\n'.join(
        f"  {g.get('home_team')} vs {g.get('away_team')}  ({g.get('kickoff_local', '')[:16]})"
        for g in fixture
    )

    results_lines = '\n'.join(
        f"  {r.get('home')} {r.get('home_score')}-{r.get('away_score')} {r.get('away')}  "
        f"(margin {r.get('margin', '?')})"
        for r in prev_results
    ) or '  (not available)'

    # Group news flags by team for readability
    by_team: dict[str, list[str]] = {}
    for flag in news_flags:
        team = flag.get('team', 'Unknown')
        line = f"  [{flag.get('flag_type','?')}] {flag.get('player_name','?')} — {flag.get('reason','?')} (severity={flag.get('severity','?')})"
        by_team.setdefault(team, []).append(line)

    news_section = ''
    for team, lines in sorted(by_team.items()):
        news_section += f"\n{team}:\n" + '\n'.join(lines)

    auto_section = (
        json.dumps(auto_flags, indent=2, ensure_ascii=False)
        if auto_flags else '  (none detected)'
    )

    return f"""UPCOMING ROUND: Season {season}, Round {round_number}

FIXTURE:
{fixture_lines}

PREVIOUS ROUND RESULTS:
{results_lines}

CURRENT NEWS FLAGS FROM BETMATE:
{news_section}

AUTO-DETECTED EMOTIONAL FLAGS (already confirmed — do NOT repeat these):
{auto_section}

Based on the above, identify any ADDITIONAL emotional flags (milestone, new_coach, star_return, farewell, personal_tragedy, must_win) for Round {round_number}.

Return a JSON array only. No prose. No markdown. No explanation outside the JSON.
"""


def call_claude(prompt: str, dry_run: bool) -> list[dict]:
    if dry_run:
        log.info('DRY RUN — skipping Claude API call')
        return []

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        log.warning('ANTHROPIC_API_KEY not set — skipping Claude analysis')
        return []

    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model='claude-opus-4-7',
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = msg.content[0].text.strip()
        log.info('Claude response: %s', raw[:200])

        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        result = json.loads(raw)
        if isinstance(result, list):
            return result
        log.warning('Claude returned non-list: %s', type(result))
        return []
    except json.JSONDecodeError as exc:
        log.warning('Claude response not valid JSON: %s', exc)
        return []
    except Exception as exc:
        log.warning('Claude API call failed: %s', exc)
        return []


def validate_flag(flag: dict, season: int, round_number: int) -> dict | None:
    """Validate and normalise a flag dict. Returns None if invalid."""
    ftype    = str(flag.get('flag_type', '')).strip().lower()
    strength = str(flag.get('flag_strength', 'normal')).strip().lower()
    team     = str(flag.get('team', '')).strip()

    if not team:
        return None
    if ftype not in VALID_FLAG_TYPES:
        log.warning('Invalid flag_type "%s" — skipping', ftype)
        return None
    if strength not in VALID_STRENGTHS:
        strength = 'normal'

    return {
        'season':       season,
        'round':        round_number,
        'team':         team,
        'flag_type':    ftype,
        'flag_strength': strength,
        'player_name':  flag.get('player_name') or None,
        'notes':        flag.get('notes') or None,
        'source_url':   flag.get('source_url') or None,
    }


def write_outputs(flags: list[dict], raw_payload: dict, season: int, round_number: int) -> None:
    scraped_at = datetime.now(timezone.utc).isoformat()

    raw_year_dir = RAW_DIR / str(season)
    raw_year_dir.mkdir(parents=True, exist_ok=True)
    (raw_year_dir / f'round-{round_number}.json').write_text(
        json.dumps(raw_payload, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    proc_year_dir = PROC_DIR / str(season)
    proc_year_dir.mkdir(parents=True, exist_ok=True)
    (proc_year_dir / f'round-{round_number}.json').write_text(
        json.dumps(flags, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    if flags:
        PROC_DIR.mkdir(parents=True, exist_ok=True)
        (PROC_DIR / 'latest-emotional.json').write_text(
            json.dumps({
                'sport':      'NRL',
                'season':     season,
                'round':      round_number,
                'scraped_at': scraped_at,
                'flags':      flags,
            }, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        log.info('Wrote latest-emotional.json — %d flags, R%d', len(flags), round_number)
    else:
        log.info('No flags generated — latest-emotional.json NOT overwritten')


def get_prev_results_from_db(db_path: str | None, prev_round: int, season: int) -> list[dict]:
    if not db_path or not Path(db_path).exists():
        return []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT h.team_name AS home, a.team_name AS away,
                   r.home_score, r.away_score,
                   ABS(r.home_score - r.away_score) AS margin
            FROM   results r
            JOIN   matches m ON m.match_id     = r.match_id
            JOIN   teams   h ON h.team_id      = m.home_team_id
            JOIN   teams   a ON a.team_id      = m.away_team_id
            WHERE  m.season = ? AND m.round_number = ?
              AND  r.result_status = 'final'
            """,
            (season, prev_round),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        log.warning('Could not fetch prev results: %s', exc)
        return []


def run(season: int, round_number: int, db_path: str | None, dry_run: bool) -> int:
    prev_round = round_number - 1

    fixture_path    = ROOT / 'data' / 'nrl' / 'fixture' / 'processed' / 'latest-fixture.json'
    news_flags_path = ROOT / 'data' / 'nrl' / 'news_flags' / 'processed' / 'latest.json'

    fixture_data = load_json(fixture_path) or {}
    fixture      = fixture_data.get('games', []) if isinstance(fixture_data, dict) else []
    news_flags   = load_json(news_flags_path) or []
    prev_results = get_prev_results_from_db(db_path, prev_round, season) if prev_round >= 1 else []

    if not fixture:
        log.warning('No fixture data — emotional flags may be incomplete')

    # ── Deterministic detections ──────────────────────────────────────────
    auto_flags: list[dict] = []

    shame_flags = detect_shame_blowout(db_path, prev_round, season)
    auto_flags.extend(shame_flags)

    derby_flags = detect_rivalry_derby(fixture, season, round_number)
    auto_flags.extend(derby_flags)

    origin_result = detect_origin_boost(fixture, season, round_number)
    # origin_result is a sentinel if window active; handled in Claude prompt context
    origin_active = bool(origin_result and '_origin_window' in origin_result[0])

    log.info(
        'Auto-detected: %d shame_blowout, %d rivalry_derby, origin_boost=%s',
        len(shame_flags), len(derby_flags), origin_active,
    )

    # ── Claude analysis ───────────────────────────────────────────────────
    prompt = build_claude_prompt(
        season, round_number, fixture, prev_results, news_flags, auto_flags,
    )
    if origin_active:
        prompt += f"\n\nNOTE: This round falls in a post-Origin camp window ({origin_result[0]['_origin_window']}). Consider origin_boost flags for teams with high Origin representation."

    claude_flags = call_claude(prompt, dry_run)
    log.info('Claude returned %d additional flags', len(claude_flags))

    # ── Merge + validate ──────────────────────────────────────────────────
    all_raw = auto_flags + claude_flags
    validated: list[dict] = []
    for flag in all_raw:
        v = validate_flag(flag, season, round_number)
        if v:
            validated.append(v)

    # Deduplicate by (team, flag_type, player_name)
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for v in validated:
        key = (v['team'], v['flag_type'], v.get('player_name'))
        if key not in seen:
            seen.add(key)
            deduped.append(v)

    log.info('Final: %d validated flags after dedup', len(deduped))

    if not dry_run:
        write_outputs(deduped, {
            'season': season, 'round': round_number,
            'auto_flags': auto_flags, 'claude_flags': claude_flags,
            'prompt': prompt,
        }, season, round_number)
    else:
        log.info('DRY RUN — output:')
        print(json.dumps(deduped, indent=2, ensure_ascii=False))

    # Print summary
    if deduped:
        print(f'\n  Emotional flags for R{round_number}:')
        for f in deduped:
            player = f' — {f["player_name"]}' if f.get('player_name') else ''
            print(f'  [{f["flag_type"]:<18}] {f["flag_strength"]:<6}  {f["team"]}{player}')
            if f.get('notes'):
                print(f'    {f["notes"]}')
    else:
        print(f'\n  No emotional flags for R{round_number} this week.')

    return len(deduped)


def main() -> None:
    setup_logging()
    p = argparse.ArgumentParser(description='Generate T7 emotional flags for NRL round')
    p.add_argument('--season',   type=int, default=2026)
    p.add_argument('--round',    type=int, required=True, dest='round_number',
                   help='Round to generate flags for')
    p.add_argument('--db-path',  default=None,
                   help='Path to BettingEngine model.db (enables shame_blowout detection)')
    p.add_argument('--dry-run',  action='store_true',
                   help='Print output without writing files or calling Claude')
    args = p.parse_args()

    # Try to auto-find BettingEngine DB if not supplied
    db_path = args.db_path
    if not db_path:
        candidate = ROOT.parent / 'BettingEngine' / 'data' / 'model.db'
        if candidate.exists():
            db_path = str(candidate)
            log.info('Auto-found BettingEngine DB: %s', db_path)

    log.info('Generating emotional flags: season=%d round=%d', args.season, args.round_number)
    count = run(args.season, args.round_number, db_path, args.dry_run)
    sys.exit(0 if count >= 0 else 1)


if __name__ == '__main__':
    main()
