#!/usr/bin/env python3
"""FotMob adapter: fixtures, predicted/confirmed XIs, and player availability.

Covers EPL, EFL Championship and UCL from one endpoint. Verified 2026-09-13 —
see cloud/sources/README.md for what was tested and what was rejected.

Two calls:
    /api/data/matches?date=YYYYMMDD      fixtures for a day, grouped by league
    /api/data/matchDetails?matchId=ID    lineup + unavailable players

⚠️ `lineup_type` is the confidence marker and is never inferred. Observed ladder,
   furthest from kickoff to nearest:

       lastStarting11  last week's XI - NOT a prediction, just the previous team
       predicted       a real predicted XI (seen from ~T-2d)
       standard        the actual XI, once the match has started
       confirmed       expected ~T-1h; not yet observed in the wild, handle it

   Anything downstream that flattens those into one field is reading fiction.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Iterable
from urllib.request import Request, urlopen

BASE = "https://www.fotmob.com/api/data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# (fotmob league name, ccode) -> our code. FotMob has many leagues called
# "Premier League" - Ghana, Russia, Belarus and a dozen more - so the ccode is
# load bearing, not decoration. Matching on name alone pulls Canadian fixtures.
LEAGUES: dict[str, tuple[str, str]] = {
    "EPL": ("Premier League", "ENG"),
    "EFL": ("Championship", "ENG"),
    "UCL": ("Champions League", "INT"),
}

MIN_INTERVAL_SECONDS = 1.5   # be a good citizen; ESPN throttled us the same morning
_last_call = 0.0


@dataclass
class Player:
    source_player_id: str | None
    name: str
    shirt_number: int | None = None
    position: str | None = None


@dataclass
class Absence:
    source_player_id: str | None
    name: str
    reason_type: str | None          # "injury", "suspension", ...
    reason_detail: str | None        # free text where given
    expected_return: str | None      # "Mid October 2026" / "Doubtful" - kept VERBATIM


@dataclass
class TeamSheet:
    code: str
    source_match_id: str
    kickoff_utc: str
    home_team: str
    away_team: str
    side: str                        # "home" | "away"
    team_name: str
    lineup_type: str                 # confirmed | predicted | lastStarting11
    formation: str | None
    starters: list[Player] = field(default_factory=list)
    unavailable: list[Absence] = field(default_factory=list)
    source: str = "fotmob"
    captured_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["starters"] = [asdict(p) for p in self.starters]
        d["unavailable"] = [asdict(a) for a in self.unavailable]
        return d


def _get(url: str) -> dict:
    global _last_call
    wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        _last_call = time.monotonic()
        return json.loads(resp.read())


def fixtures_for_day(day: date, codes: Iterable[str] = ("EPL", "EFL", "UCL")) -> list[dict]:
    """Fixtures on one day for the codes we care about. One free call per day."""
    payload = _get(f"{BASE}/matches?date={day:%Y%m%d}")
    wanted = {LEAGUES[c]: c for c in codes if c in LEAGUES}
    out: list[dict] = []
    for league in payload.get("leagues", []):
        key = (league.get("name"), league.get("ccode"))
        code = wanted.get(key)
        if not code:
            continue
        for match in league.get("matches", []):
            status = match.get("status", {}) or {}
            out.append({
                "code": code,
                "source_match_id": str(match.get("id")),
                "kickoff_utc": status.get("utcTime"),
                "started": bool(status.get("started")),
                "home_team": (match.get("home") or {}).get("name"),
                "away_team": (match.get("away") or {}).get("name"),
            })
    return out


def _players(raw: list[dict]) -> list[Player]:
    return [Player(source_player_id=str(p.get("id")) if p.get("id") is not None else None,
                   name=p.get("name") or "",
                   shirt_number=p.get("shirtNumber"),
                   position=str(p.get("positionId")) if p.get("positionId") is not None else None)
            for p in raw or []]


def _absences(raw: list[dict]) -> list[Absence]:
    out = []
    for p in raw or []:
        u = p.get("unavailability") or {}
        out.append(Absence(
            source_player_id=str(p.get("id")) if p.get("id") is not None else None,
            name=p.get("name") or "",
            reason_type=u.get("type"),
            reason_detail=u.get("reason"),
            # Kept as the source wrote it. FotMob mixes a date band ("Mid October
            # 2026") with a status word ("Doubtful") in the same field; parsing
            # that into a timestamp here would invent precision the source never
            # claimed. Normalise downstream, where the loss is visible.
            expected_return=u.get("expectedReturn"),
        ))
    return out


def team_sheets(fixture: dict) -> list[TeamSheet]:
    """Both sides of one fixture. Empty list when FotMob has no lineup yet."""
    details = _get(f"{BASE}/matchDetails?matchId={fixture['source_match_id']}")
    lineup = (details.get("content") or {}).get("lineup") or {}
    if not lineup:
        return []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sheets = []
    for side, key in (("home", "homeTeam"), ("away", "awayTeam")):
        team = lineup.get(key) or {}
        if not team:
            continue
        sheets.append(TeamSheet(
            code=fixture["code"],
            source_match_id=fixture["source_match_id"],
            kickoff_utc=fixture["kickoff_utc"],
            home_team=fixture["home_team"],
            away_team=fixture["away_team"],
            side=side,
            team_name=team.get("name") or "",
            lineup_type=lineup.get("lineupType") or "unknown",
            formation=team.get("formation"),
            starters=_players(team.get("starters")),
            unavailable=_absences(team.get("unavailable")),
            captured_at=now,
        ))
    return sheets


def upcoming(days_ahead: int = 4, codes: Iterable[str] = ("EPL", "EFL", "UCL"),
             include_started: bool = False) -> list[dict]:
    """Fixtures from now to `days_ahead`. One call per day, so cheap.

    Started matches are excluded by default: today's list includes games that
    kicked off hours ago, and their lineup_type is `standard` (the real XI), which
    is useless for a forward-looking teamsheet and would pollute any lead-time
    analysis with rows at negative hours-to-kickoff.
    """
    today = datetime.now(timezone.utc).date()
    out = []
    for delta in range(days_ahead + 1):
        for fx in fixtures_for_day(today + timedelta(days=delta), codes):
            if not include_started and fx.get("started"):
                continue
            out.append(fx)
    return out


if __name__ == "__main__":  # smoke test: prove the source is alive before trusting it
    fixtures = upcoming(days_ahead=2)
    print(f"{len(fixtures)} fixtures in the next 3 days")
    for fx in fixtures[:3]:
        sheets = team_sheets(fx)
        if not sheets:
            print(f"  {fx['code']:<4} {fx['home_team']} v {fx['away_team']}: no lineup yet")
            continue
        s = sheets[0]
        print(f"  {fx['code']:<4} {fx['home_team']} v {fx['away_team']}: "
              f"type={s.lineup_type} XI={len(s.starters)} out={len(s.unavailable)}")
        for a in s.unavailable[:3]:
            print(f"        {a.name} ({a.reason_type}) -> {a.expected_return}")
