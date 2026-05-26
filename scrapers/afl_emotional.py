"""
lib/scraper/afl_emotional.py

Generates emotional flags for the upcoming AFL round.

Data sources:
  - BettingEngine/outputs/afl_round_prep/rNN_YYYY/fixture_rNN_YYYY.csv  — fixture
  - data/afl/injuries/processed/latest-injuries.json                     — injuries
  - data/afl/team-news/latest.json                                        — team news
  - ANTHROPIC_API_KEY env var (from .env.local)

Deterministic:
  - rivalry_derby: fixture vs known AFL rivalry pair

Claude layer:
  - milestone, star_return, must_win, new_coach, farewell, personal_tragedy

Output:
  data/afl/emotional/raw/YYYY/round-N.json
  data/afl/emotional/processed/YYYY/round-N.json
  data/afl/emotional/processed/latest-emotional.json
  data/afl/emotional/logs/scrape.log

Usage:
  uv run --with anthropic python lib/scraper/afl_emotional.py --round 11
  uv run --with anthropic python lib/scraper/afl_emotional.py --round 0    # auto-detect
  uv run --with anthropic python lib/scraper/afl_emotional.py --round 11 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT      = Path(__file__).resolve().parents[1]
BASE_DIR  = ROOT / "data" / "afl" / "emotional"
RAW_DIR   = BASE_DIR / "raw"
PROC_DIR  = BASE_DIR / "processed"
LOG_DIR   = BASE_DIR / "logs"
LOG_PATH  = LOG_DIR / "scrape.log"

BETENGINE = ROOT / "BettingEngine"

VALID_FLAG_TYPES = {
    'milestone', 'new_coach', 'star_return',
    'farewell', 'personal_tragedy', 'rivalry_derby', 'must_win',
}
VALID_STRENGTHS = {'minor', 'normal', 'major'}

# Known AFL rivalry pairs — both orderings are checked
RIVALRIES: list[frozenset[str]] = [
    frozenset({'Collingwood Magpies', 'Carlton Blues'}),
    frozenset({'Collingwood Magpies', 'Richmond Tigers'}),
    frozenset({'Collingwood Magpies', 'Essendon Bombers'}),
    frozenset({'Carlton Blues', 'Essendon Bombers'}),
    frozenset({'Hawthorn Hawks', 'Essendon Bombers'}),           # Freeway Derby
    frozenset({'Richmond Tigers', 'Essendon Bombers'}),          # MCG rivals
    frozenset({'Hawthorn Hawks', 'Richmond Tigers'}),            # MCG rivals
    frozenset({'Melbourne Demons', 'Richmond Tigers'}),          # MCG rivals
    frozenset({'Geelong Cats', 'Collingwood Magpies'}),
    frozenset({'Geelong Cats', 'Hawthorn Hawks'}),
    frozenset({'Geelong Cats', 'Sydney Swans'}),                 # modern grand final rivalry
    frozenset({'Fremantle Dockers', 'West Coast Eagles'}),       # WA Derby
    frozenset({'Port Adelaide Power', 'Adelaide Crows'}),        # The Showdown
    frozenset({'Sydney Swans', 'Greater Western Sydney Giants'}),# Sydney Derby
    frozenset({'Brisbane Lions', 'Gold Coast Suns'}),            # Queensland Derby
    frozenset({'Melbourne Demons', 'Collingwood Magpies'}),
    frozenset({'North Melbourne Kangaroos', 'Collingwood Magpies'}),
    frozenset({'St Kilda Saints', 'Collingwood Magpies'}),
    frozenset({'Western Bulldogs', 'Collingwood Magpies'}),
]

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the AFL emotional context analyst for a sports pricing engine.

Your job is to identify MEANINGFUL emotional/motivational storylines that will materially
affect a team's performance in the upcoming round. You are conservative — most games have
no emotional flags. Expect 0–2 per round total.

You will receive:
1. The upcoming round fixture
2. Current injury/suspension/team news from BetMate
3. Auto-detected flags (rivalry_derby) already confirmed

Your task: identify any ADDITIONAL flags from these types only:
  milestone        — 100th/150th/200th/250th/300th AFL game, debut, first game as captain
  new_coach        — first game under a newly appointed head coach
  star_return      — elite/key player returning from 3+ weeks injured
  farewell         — confirmed retirement game, player's last season announcement
  personal_tragedy — team rallying around a recent death, serious illness, family tragedy
  must_win         — team effectively eliminated without a win, OR team in bottom 4 of
                     ladder with ≤6 rounds left and on a 3+ game losing streak

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
Only include flags you are CONFIDENT about from the provided data. Do not speculate.
Do not repeat flags already in the auto-detected list.
Use full canonical AFL team names (e.g. "Collingwood Magpies" not "Magpies").
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


def auto_detect_round() -> int | None:
    """Find the highest round number in BettingEngine afl_round_prep outputs."""
    prep_base = BETENGINE / 'outputs' / 'afl_round_prep'
    if not prep_base.exists():
        return None
    dirs = [
        d for d in prep_base.iterdir()
        if d.is_dir() and re.match(r'^r(\d+)_\d{4}$', d.name)
    ]
    if not dirs:
        return None
    dirs.sort(key=lambda d: int(re.match(r'^r(\d+)_', d.name).group(1)))
    latest = dirs[-1]
    m = re.match(r'^r(\d+)_', latest.name)
    return int(m.group(1)) if m else None


def load_fixture(round_number: int, season: int) -> list[dict]:
    """Read fixture CSV from BettingEngine round prep output."""
    fixture_path = BETENGINE / 'outputs' / 'afl_round_prep' / f'r{round_number}_{season}' / f'fixture_r{round_number}_{season}.csv'
    if not fixture_path.exists():
        log.warning('AFL fixture not found: %s', fixture_path)
        return []
    games = []
    with open(fixture_path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            games.append({
                'home_team':     row.get('home_team', ''),
                'away_team':     row.get('away_team', ''),
                'venue':         row.get('venue', ''),
                'kickoff_local': row.get('date', ''),
            })
    log.info('Loaded %d games from fixture CSV', len(games))
    return games


def detect_rivalry_derby(fixture: list[dict]) -> list[dict]:
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
                'notes':         f'{home} vs {away} is a recognised AFL rivalry fixture.',
                'source':        'fixture_rivalry',
            })
            log.info('rivalry_derby detected: %s vs %s', home, away)
    return flags


def build_claude_prompt(
    season: int,
    round_number: int,
    fixture: list[dict],
    injuries: list[dict],
    team_news: dict,
    auto_flags: list[dict],
) -> str:
    fixture_lines = '\n'.join(
        f"  {g.get('home_team')} vs {g.get('away_team')}  ({g.get('kickoff_local', '')[:10]})"
        for g in fixture
    ) or '  (no fixture loaded)'

    # Injuries grouped by team
    by_team: dict[str, list[str]] = {}
    for inj in injuries:
        team = inj.get('team', 'Unknown')
        line = f"  [{inj.get('status','?')}] {inj.get('player','?')} — {inj.get('notes','')}"
        by_team.setdefault(team, []).append(line)

    injury_section = ''
    for team, lines in sorted(by_team.items()):
        injury_section += f"\n{team}:\n" + '\n'.join(lines)

    # Team news (different format — nested dict by team with items list)
    news_section = ''
    if isinstance(team_news, dict):
        teams_data = team_news.get('teams', team_news)
        for team, data in sorted(teams_data.items()):
            items = data.get('items', []) if isinstance(data, dict) else []
            if items:
                news_section += f"\n{team}:\n"
                for item in items:
                    news_section += f"  [{item.get('type','?')}] {item.get('player','?')} — {item.get('detail','')}\n"

    auto_section = (
        json.dumps(auto_flags, indent=2, ensure_ascii=False)
        if auto_flags else '  (none detected)'
    )

    return f"""UPCOMING ROUND: Season {season}, Round {round_number}

FIXTURE:
{fixture_lines}

INJURY LIST:
{injury_section or '  (none loaded)'}

TEAM NEWS:
{news_section or '  (none loaded)'}

AUTO-DETECTED EMOTIONAL FLAGS (already confirmed — do NOT repeat these):
{auto_section}

Based on the above, identify any ADDITIONAL emotional flags for Round {round_number}.

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
        'season':        season,
        'round':         round_number,
        'team':          team,
        'flag_type':     ftype,
        'flag_strength': strength,
        'player_name':   flag.get('player_name') or None,
        'notes':         flag.get('notes') or None,
    }


def write_outputs(flags: list[dict], raw_payload: dict, season: int, round_number: int) -> None:
    scraped_at = datetime.now(timezone.utc).isoformat()

    raw_year_dir = RAW_DIR / str(season)
    raw_year_dir.mkdir(parents=True, exist_ok=True)
    (raw_year_dir / f'round-{round_number}.json').write_text(
        json.dumps(raw_payload, indent=2, ensure_ascii=False), encoding='utf-8',
    )

    proc_year_dir = PROC_DIR / str(season)
    proc_year_dir.mkdir(parents=True, exist_ok=True)
    (proc_year_dir / f'round-{round_number}.json').write_text(
        json.dumps(flags, indent=2, ensure_ascii=False), encoding='utf-8',
    )

    if flags:
        PROC_DIR.mkdir(parents=True, exist_ok=True)
        (PROC_DIR / 'latest-emotional.json').write_text(
            json.dumps({
                'sport':      'AFL',
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


def run(season: int, round_number: int, dry_run: bool) -> int:
    fixture  = load_fixture(round_number, season)
    injuries = load_json(ROOT / 'data' / 'afl' / 'injuries' / 'processed' / 'latest-injuries.json') or []
    team_news = load_json(ROOT / 'data' / 'afl' / 'team-news' / 'latest.json') or {}

    if not fixture:
        log.warning('No fixture data — emotional flags may be incomplete')

    auto_flags = detect_rivalry_derby(fixture)
    log.info('Auto-detected: %d rivalry_derby', len(auto_flags))

    prompt = build_claude_prompt(season, round_number, fixture, injuries, team_news, auto_flags)
    claude_flags = call_claude(prompt, dry_run)
    log.info('Claude returned %d additional flags', len(claude_flags))

    all_raw = auto_flags + claude_flags
    validated: list[dict] = []
    for flag in all_raw:
        v = validate_flag(flag, season, round_number)
        if v:
            validated.append(v)

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

    if deduped:
        print(f'\n  AFL Emotional flags for R{round_number}:')
        for f in deduped:
            player = f' — {f["player_name"]}' if f.get('player_name') else ''
            print(f'  [{f["flag_type"]:<18}] {f["flag_strength"]:<6}  {f["team"]}{player}')
            if f.get('notes'):
                print(f'    {f["notes"]}')
    else:
        print(f'\n  No AFL emotional flags for R{round_number} this week.')

    return len(deduped)


def main() -> None:
    setup_logging()
    p = argparse.ArgumentParser(description='Generate emotional flags for AFL round')
    p.add_argument('--season',  type=int, default=2026)
    p.add_argument('--round',   type=int, required=True, dest='round_number',
                   help='Round to generate flags for (0 = auto-detect)')
    p.add_argument('--dry-run', action='store_true',
                   help='Print output without writing files or calling Claude')
    args = p.parse_args()

    round_number = args.round_number
    if round_number == 0:
        round_number = auto_detect_round()
        if not round_number:
            log.error('Could not auto-detect AFL round — pass --round explicitly')
            sys.exit(1)
        log.info('Auto-detected round: %d', round_number)

    log.info('Generating AFL emotional flags: season=%d round=%d', args.season, round_number)
    count = run(args.season, round_number, args.dry_run)
    sys.exit(0 if count >= 0 else 1)


if __name__ == '__main__':
    main()
