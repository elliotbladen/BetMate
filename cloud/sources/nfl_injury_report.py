#!/usr/bin/env python3
"""NFL adapter: the league-mandated injury report from NFL.com.

The NFL is the only code in this project with a MANDATED injury report. Clubs must
file practice participation on each practice day and a game-status designation
before kickoff. That makes nfl.com/injuries a primary source rather than an
aggregator - RotoWire, ESPN and the rest are all reporting this same filing, so
going to the source removes a hop and a chance to be stale.

Verified 2026-09-13: server-rendered HTML, 366 KB, no JS required. Counts on the
page that day - Full Participation 96, Limited 50, Did Not Participate 36,
Questionable 24, Doubtful 6.

⚠️ There is NO __NEXT_DATA__ blob, so this is HTML parsing, not a JSON lift. That
   is the trade for using the authoritative source, and it means this adapter WILL
   break when NFL.com changes markup. It fails loudly rather than returning an
   empty list, because a silent empty injury report reads exactly like a healthy
   squad - and this repo has been bitten four times in two days by things that
   report success while doing nothing.

The two fields mean different things and are both kept:
    practice_status  DNP / Limited / Full      - what they did in training
    game_status      Out / Doubtful / Questionable - whether they will play
Game status is only filed later in the week; early in the week practice status is
all there is, which is exactly the 1-3 days out signal we are after.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.request import Request, urlopen

URL = "https://www.nfl.com/injuries/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

PRACTICE = ("Did Not Participate In Practice", "Limited Participation in Practice",
            "Full Participation in Practice", "Did Not Participate", "Limited Participation",
            "Full Participation")
GAME_STATUS = ("Out", "Doubtful", "Questionable")


class SourceChanged(RuntimeError):
    """NFL.com markup no longer matches. Raised rather than returning nothing."""


@dataclass
class NflAbsence:
    team: str
    player: str
    position: str | None
    injury: str | None
    practice_status: str | None
    game_status: str | None
    captured_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def fetch_html(url: str = URL) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html",
                                "Accept-Language": "en-US,en;q=0.9"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def _sanity(html: str) -> None:
    """Refuse to parse a page that cannot be the injury report.

    A markup change that yields zero rows is indistinguishable from a week where
    nobody is hurt, and the second never happens. Checking for the designations
    themselves - which are league vocabulary, not NFL.com styling - catches the
    page being replaced by a shell, a consent wall or an error page.
    """
    if len(html) < 50_000:
        raise SourceChanged(f"page is only {len(html)} bytes; expected ~350KB")
    hits = sum(html.count(word) for word in PRACTICE + GAME_STATUS)
    if hits < 20:
        raise SourceChanged(
            f"only {hits} injury designations found in {len(html)} bytes - "
            "NFL.com markup has probably changed, or the page is client-rendered now"
        )


def parse(html: str) -> list[NflAbsence]:
    """One row per player, from the per-team tables.

    The page renders 32 tables - one per club - each with a fixed header:
        Player | Position | Injuries | Practice Status | Game Status
    and each preceded in document order by a `nfl-c-matchup-strip__team-fullname`
    anchor naming the club. Binding each table to its nearest preceding anchor is
    what attributes a player to the right team.

    Cells are read POSITIONALLY and empties are preserved. Early in the week the
    Injuries and Game Status cells are blank - clubs only have to file a game
    status later - so dropping empty cells would shift every remaining value one
    column left and silently mislabel a practice status as an injury.
    """
    _sanity(html)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    anchors = [(m.start(), m.group(1)) for m in
               re.finditer(r'nfl-c-matchup-strip__team-fullname"[^>]*href="/teams/([a-z0-9-]+)/"', html)]
    tables = [(m.start(), m.group(0)) for m in re.finditer(r"<table.*?</table>", html, re.S)]
    if not tables:
        raise SourceChanged("no <table> elements found on the injury report")

    # Pair by INDEX, not proximity. Each matchup strip names both clubs BEFORE
    # either table appears (anchor_away, anchor_home, table_away, table_home), so
    # "nearest preceding anchor" hands every table the second club and silently
    # files half the league's injuries against the wrong team. Caught because
    # Christian Barmore came back as a Seahawk; he is a Patriot.
    if len(anchors) != len(tables):
        raise SourceChanged(
            f"{len(anchors)} team anchors but {len(tables)} tables - cannot pair them safely"
        )

    out: list[NflAbsence] = []
    for (_, slug), (_, table) in zip(anchors, tables):
        team = slug.replace("-", " ").title()
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
            if len(cells) < 5 or cells[0] in ("", "Player"):
                continue
            player, position, injury, practice, game = cells[:5]
            out.append(NflAbsence(
                team=team,
                player=player,
                position=position or None,
                injury=injury or None,
                practice_status=practice or None,
                game_status=game or None,
                captured_at=now,
            ))
    if not out:
        raise SourceChanged(f"{len(tables)} tables found but no player rows parsed")
    return out


def collect() -> list[NflAbsence]:
    return parse(fetch_html())


if __name__ == "__main__":
    try:
        rows = collect()
    except SourceChanged as exc:
        raise SystemExit(f"NFL source check FAILED: {exc}")
    print(f"parsed {len(rows)} injury rows from nfl.com/injuries")
    by_status: dict[str, int] = {}
    for r in rows:
        key = r.game_status or r.practice_status or "?"
        by_status[key] = by_status.get(key, 0) + 1
    for k, v in sorted(by_status.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<34} {v}")
    for r in rows[:5]:
        print(f"  e.g. {r.team:<16} {r.player:<22} {r.game_status or r.practice_status}")
