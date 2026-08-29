#!/usr/bin/env python3
"""
scrape_team_lists.py — Scrape NRL + AFL team lists (ins/outs) at announcement time.

NRL: Tuesday 4:00pm AEST from legz.com.au
AFL: Thursday 6:20pm AEST from footywire.com

Outputs JSON to data/line_movement/team_lists/{sport}_r{round}_{date}.json

Usage:
    python scripts/line_mover/scrape_team_lists.py --sport NRL
    python scripts/line_mover/scrape_team_lists.py --sport AFL
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "line_movement" / "team_lists"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ---------------------------------------------------------------------------
# NRL — legz.com.au
# ---------------------------------------------------------------------------

NRL_URL = "https://www.legz.com.au/nrl/team-lists"


def scrape_nrl_team_lists() -> dict:
    """Scrape NRL team lists from legz.com.au. Returns structured dict."""
    resp = requests.get(NRL_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Try to find embedded JSON data first
    result = {"sport": "NRL", "scraped_at": datetime.now(timezone.utc).isoformat(), "teams": {}}

    # Legz is a Next.js app. Its complete, structured change data lives in
    # __NEXT_DATA__; parsing rendered div text is both lossy and brittle.
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            payload = json.loads(next_data.string)
            data = payload["props"]["pageProps"]["data"]
            matches = data.get("matches", [])
            page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
            title_round = re.search(r"Round\s+(\d+)", page_title, re.IGNORECASE)
            if title_round:
                result["round"] = int(title_round.group(1))
            for match in matches:
                round_value = match.get("match", {}).get("nrl_round", {}).get("round_number")
                if round_value:
                    result["round"] = int(round_value)
                for side in ("home", "away"):
                    entry = match.get(side) or {}
                    team = (entry.get("team") or {}).get("name")
                    if not team:
                        continue
                    ins = [
                        item.get("player", {}).get("name")
                        for item in entry.get("ins", [])
                        if item.get("player", {}).get("name")
                    ]
                    outs = [
                        item.get("player", {}).get("name")
                        for item in entry.get("outs", [])
                        if item.get("player", {}).get("name")
                    ]
                    if ins or outs:
                        result["teams"][team] = {"ins": ins, "outs": outs}
            if result["teams"]:
                return result
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass

    # Look for round info in page title/headers
    title = soup.find("title")
    if title:
        result["page_title"] = title.get_text(strip=True)
        m = re.search(r"Round\s+(\d+)", title.get_text())
        if m:
            result["round"] = int(m.group(1))
    if not result.get("round"):
        page_round = re.search(r"Round\s*(\d+)", soup.get_text(" ", strip=True))
        if page_round:
            result["round"] = int(page_round.group(1))

    # Parse team sections — legz uses match cards with team names and player lists
    # Look for ins/outs sections
    for section in soup.find_all(["div", "section"]):
        text = section.get_text(" ", strip=True)

        # Find team name patterns
        team_match = re.search(
            r"(Broncos|Raiders|Bulldogs|Sharks|Dolphins|Titans|Sea Eagles|Storm|"
            r"Knights|Warriors|Cowboys|Eels|Panthers|Rabbitohs|Dragons|Roosters|"
            r"Wests Tigers|Bears|Chiefs)",
            text,
        )
        if not team_match:
            continue

        team_name = team_match.group(1)
        if team_name in result["teams"]:
            continue

        # Look for ins/outs
        ins = []
        outs = []
        ins_match = re.search(r"Ins?\s*(?:vs\s+R\d+)?[:\s]+([A-Z][\w\s,'.()-]+?)(?:Outs?|$)", text)
        outs_match = re.search(r"Outs?\s*(?:vs\s+R\d+)?[:\s]+([A-Z][\w\s,'.()-]+?)(?:Ins?|$)", text)

        if ins_match:
            ins = [n.strip() for n in ins_match.group(1).split(",") if n.strip() and len(n.strip()) > 2]
        if outs_match:
            outs = [n.strip() for n in outs_match.group(1).split(",") if n.strip() and len(n.strip()) > 2]

        if ins or outs:
            result["teams"][team_name] = {"ins": ins, "outs": outs}

    # Fallback: try to extract from script tags (embedded JSON)
    if not result["teams"]:
        for script in soup.find_all("script"):
            script_text = script.string or ""
            if "team" in script_text.lower() and "player" in script_text.lower():
                # Try to extract JSON objects
                for m in re.finditer(r'\{[^{}]*"team"[^{}]*\}', script_text):
                    try:
                        data = json.loads(m.group())
                        if "team" in data:
                            result["raw_json_found"] = True
                            break
                    except json.JSONDecodeError:
                        continue

    return result


# ---------------------------------------------------------------------------
# AFL — footywire.com
# ---------------------------------------------------------------------------

AFL_URL = "https://www.footywire.com/afl/footy/afl_team_selections"

AFL_TEAM_MAP = {
    "Adelaide": "Adelaide Crows",
    "Brisbane Lions": "Brisbane Lions",
    "Brisbane": "Brisbane Lions",
    "Carlton": "Carlton Blues",
    "Collingwood": "Collingwood Magpies",
    "Essendon": "Essendon Bombers",
    "Fremantle": "Fremantle Dockers",
    "Geelong": "Geelong Cats",
    "Gold Coast": "Gold Coast Suns",
    "GWS Giants": "Greater Western Sydney Giants",
    "GWS": "Greater Western Sydney Giants",
    "Hawthorn": "Hawthorn Hawks",
    "Melbourne": "Melbourne Demons",
    "North Melbourne": "North Melbourne Kangaroos",
    "Port Adelaide": "Port Adelaide Power",
    "Richmond": "Richmond Tigers",
    "St Kilda": "St Kilda Saints",
    "Sydney": "Sydney Swans",
    "West Coast": "West Coast Eagles",
    "Western Bulldogs": "Western Bulldogs",
}


def parse_afl_team_lists_html(html: str) -> dict:
    """Parse a Footywire AFL selections page without assuming every team changed."""
    soup = BeautifulSoup(html, "html.parser")
    result = {"sport": "AFL", "scraped_at": datetime.now(timezone.utc).isoformat(), "teams": {}}

    # Find round info
    title = soup.find("title")
    if title:
        result["page_title"] = title.get_text(strip=True)
        m = re.search(r"Round\s+(\d+)", title.get_text())
        if m:
            result["round"] = int(m.group(1))

    if not result.get("round"):
        page_round = re.search(r"Round\s*(\d+)", soup.get_text(" ", strip=True))
        if page_round:
            result["round"] = int(page_round.group(1))

    def changes(change_table) -> dict:
        cells = [value.strip() for value in change_table.stripped_strings if value.strip()]
        parsed = {"ins": [], "outs": []}
        for key, stop in (("ins", "Outs"), ("outs", None)):
            label = "Ins" if key == "ins" else "Outs"
            if label not in cells:
                continue
            start = cells.index(label) + 1
            end = cells.index(stop, start) if stop and stop in cells[start:] else len(cells)
            parsed[key] = cells[start:end]
        return parsed

    # Each fixture is a table containing two interchange tables, one per team.
    # Some tables contain no Ins/Outs at all. The old parser filtered those out
    # and then required the remaining table count to equal the 18-team count,
    # which made the whole round fail whenever even one club was unchanged.
    names = sorted(AFL_TEAM_MAP, key=len, reverse=True)
    name_pattern = "|".join(re.escape(name) for name in names)
    matchup_re = re.compile(rf"({name_pattern})\s+v\s+({name_pattern})\s*\(")
    seen_matchups: set[tuple[str, str]] = set()
    team_order: list[str] = []
    for match in matchup_re.finditer(soup.get_text(" ", strip=True)):
        mapped = (AFL_TEAM_MAP[match.group(1)], AFL_TEAM_MAP[match.group(2)])
        if mapped not in seen_matchups:
            seen_matchups.add(mapped)
            team_order.extend(mapped)

    # Footywire emits these compact tables in the same home/away order as the
    # fixture headings. Include unchanged clubs: they still have an
    # Interchange table but no Ins or Outs labels.
    interchange_tables = []
    for table in soup.find_all("table"):
        tokens = list(table.stripped_strings)
        if tokens and tokens[0] == "Interchange" and len(tokens) <= 50:
            interchange_tables.append(table)
    if len(team_order) == len(interchange_tables):
        for team, table in zip(team_order, interchange_tables):
            result["teams"][team] = changes(table)

    if len(result["teams"]) == 18:
        return result
    result["parser_error"] = {
        "matchups": len(seen_matchups),
        "teams_parsed": len(result["teams"]),
        "interchange_tables": len(interchange_tables),
    }
    return result


def scrape_afl_team_lists() -> dict:
    """Scrape AFL team selections from footywire.com. Returns structured dict."""
    resp = requests.get(AFL_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return parse_afl_team_lists_html(resp.text)

    # Footywire has a clear structure: team headers followed by player tables
    # Look for team name headers and their associated ins/outs
    all_text = soup.get_text("\n")
    lines = all_text.split("\n")

    current_team = None
    in_ins = False
    in_outs = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for team name
        for short_name, full_name in AFL_TEAM_MAP.items():
            if line == short_name or line.startswith(short_name + " "):
                current_team = full_name
                if current_team not in result["teams"]:
                    result["teams"][current_team] = {"ins": [], "outs": []}
                in_ins = False
                in_outs = False
                break

        if not current_team:
            continue

        # Check for ins/outs headers
        if re.match(r"^Ins?:?\s*$", line, re.IGNORECASE):
            in_ins = True
            in_outs = False
            continue
        if re.match(r"^Outs?:?\s*$", line, re.IGNORECASE):
            in_outs = True
            in_ins = False
            continue

        # Check for inline ins/outs
        ins_inline = re.match(r"^Ins?:\s*(.+)", line, re.IGNORECASE)
        if ins_inline:
            names = [n.strip() for n in ins_inline.group(1).split(",") if n.strip() and len(n.strip()) > 2]
            result["teams"][current_team]["ins"].extend(names)
            in_ins = False
            continue

        outs_inline = re.match(r"^Outs?:\s*(.+)", line, re.IGNORECASE)
        if outs_inline:
            names = [n.strip() for n in outs_inline.group(1).split(",") if n.strip() and len(n.strip()) > 2]
            result["teams"][current_team]["outs"].extend(names)
            in_outs = False
            continue

        # Collect player names if in ins/outs section
        if in_ins and re.match(r"^[A-Z]", line) and len(line) > 3 and len(line) < 40:
            result["teams"][current_team]["ins"].append(line)
        elif in_outs and re.match(r"^[A-Z]", line) and len(line) > 3 and len(line) < 40:
            result["teams"][current_team]["outs"].append(line)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Scrape team lists")
    parser.add_argument("--sport", required=True, choices=["NRL", "AFL"])
    parser.add_argument("--expected-round", type=int,
                        help="Reject stale source data and preserve the last valid latest file")
    args = parser.parse_args()

    print(f"Scraping {args.sport} team lists...")

    if args.sport == "NRL":
        data = scrape_nrl_team_lists()
    else:
        data = scrape_afl_team_lists()

    rnd = data.get("round", 0)
    if args.expected_round and rnd != args.expected_round:
        print(f"ERROR: source is Round {rnd}, expected Round {args.expected_round}")
        sys.exit(2)
    if data.get("parser_error"):
        print(f"ERROR: incomplete team-list parse: {data['parser_error']}")
        sys.exit(3)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{args.sport.lower()}_r{rnd}_{date_str}.json"
    out_path = DATA_DIR / filename

    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    # Also write a latest pointer
    latest_path = DATA_DIR / f"{args.sport.lower()}_latest.json"
    with open(latest_path, "w") as f:
        json.dump(data, f, indent=2)

    teams_found = len(data.get("teams", {}))
    total_ins = sum(len(t.get("ins", [])) for t in data.get("teams", {}).values())
    total_outs = sum(len(t.get("outs", [])) for t in data.get("teams", {}).values())

    print(f"Round: {rnd}")
    print(f"Teams with ins/outs: {teams_found}")
    print(f"Total ins: {total_ins}, total outs: {total_outs}")
    print(f"Saved: {out_path}")
    print(f"Latest: {latest_path}")


if __name__ == "__main__":
    main()
