#!/usr/bin/env python3
"""Audit logged 2026 AFL totals bets using the 5% matrix-confluence rule."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import ephem

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_nrl_matrix_staking as base  # noqa: E402

LEDGER = ROOT.parent / "lib" / "researchData.ts"
DB = ROOT / "data" / "model.db"
MATRIX = ROOT / "outputs" / "afl_team_totals_matrix.xlsx"
HISTORICAL = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
OUT_DIR = ROOT / "outputs" / "results"
MIN_EDGE = 5.0

ALIASES = {
    "Adelaide Crows": ["adelaide crows", "adelaide", "crows"],
    "Brisbane Lions": ["brisbane lions", "brisbane", "lions"],
    "Carlton Blues": ["carlton blues", "carlton"],
    "Collingwood Magpies": ["collingwood magpies", "collingwood", "pies"],
    "Essendon Bombers": ["essendon bombers", "essendon", "bombers"],
    "Fremantle Dockers": ["fremantle dockers", "fremantle", "dockers"],
    "Geelong Cats": ["geelong cats", "geelong", "cats"],
    "Gold Coast Suns": ["gold coast suns", "gold coast", "suns"],
    "Greater Western Sydney Giants": ["greater western sydney giants", "gws giants", "gws", "giants"],
    "Hawthorn Hawks": ["hawthorn hawks", "hawthorn", "hawks"],
    "Melbourne Demons": ["melbourne demons", "melbourne", "demons"],
    "North Melbourne Kangaroos": ["north melbourne kangaroos", "north melbourne", "kangaroos"],
    "Port Adelaide Power": ["port adelaide power", "port adelaide", "power"],
    "Richmond Tigers": ["richmond tigers", "richmond", "tigers"],
    "St Kilda Saints": ["st kilda saints", "st kilda", "saints"],
    "Sydney Swans": ["sydney swans", "sydney", "swans"],
    "West Coast Eagles": ["west coast eagles", "west coast", "eagles"],
    "Western Bulldogs": ["western bulldogs", "w bulldogs", "bulldogs"],
}

MATRIX_KEY = {
    "Adelaide Crows": "Adelaide", "Brisbane Lions": "Brisbane", "Carlton Blues": "Carlton",
    "Collingwood Magpies": "Collingwood", "Essendon Bombers": "Essendon", "Fremantle Dockers": "Fremantle",
    "Geelong Cats": "Geelong", "Gold Coast Suns": "Gold Coast", "Greater Western Sydney Giants": "GWS Giants",
    "Hawthorn Hawks": "Hawthorn", "Melbourne Demons": "Melbourne", "North Melbourne Kangaroos": "North Melbourne",
    "Port Adelaide Power": "Port Adelaide", "Richmond Tigers": "Richmond", "St Kilda Saints": "St Kilda",
    "Sydney Swans": "Sydney", "West Coast Eagles": "West Coast", "Western Bulldogs": "Western Bulldogs",
}


def parse_bets() -> list[base.Bet]:
    text = LEDGER.read_text(encoding="utf-8-sig")
    bets = []
    for item in re.finditer(r"\{\s*id:(\d+),(.*?)\}\s*,?", text, re.S):
        ident, body = int(item.group(1)), item.group(2)
        fields = dict(re.findall(r"\b(date|match|market|result|sport|notes):'([^']*)'", body))
        if fields.get("sport") != "AFL" or not fields.get("date", "").startswith("2026-"):
            continue
        odds = re.search(r"\bodds:([0-9.]+|null)", body)
        if not odds or odds.group(1) == "null": continue
        stake = re.search(r"Stake \$([0-9]+(?:\.[0-9]{1,2})?)", fields.get("notes", ""), re.I)
        bets.append(base.Bet(ident, fields["date"], fields.get("match", ""), fields.get("market", ""), float(odds.group(1)), fields.get("result", ""), float(stake.group(1)) if stake else 50.0))
    return sorted(bets, key=lambda b: (b.date, b.ident))


def teams_in(text: str) -> list[str]:
    low, found = text.lower(), []
    matched_aliases: dict[str, list[str]] = {}
    for team, aliases in ALIASES.items():
        hits = [alias for alias in aliases if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", low)]
        if hits:
            found.append(team)
            matched_aliases[team] = hits
    # Prevent shorthand aliases inside another club name from creating a false
    # second team (e.g. "Melbourne" inside "North Melbourne", or "Sydney"
    # inside "Greater Western Sydney").
    keep = []
    for team in found:
        own = max(matched_aliases[team], key=len)
        if any(team != other and any(own in other_alias and len(other_alias) > len(own) for other_alias in matched_aliases[other]) for other in found):
            continue
        keep.append(team)
    return keep


def fixtures() -> list[dict]:
    """Use the AFL historical workbook; AFL fixtures are not in model.db."""
    import openpyxl
    wb = openpyxl.load_workbook(HISTORICAL, read_only=True, data_only=True)
    games = []
    for raw in wb.active.iter_rows(min_row=3, values_only=True):
        day, ko, home_raw, away_raw, venue, hs, ascore = raw[:7]
        if not day or not hasattr(day, "year") or day.year != 2026:
            continue
        home, away = teams_in(str(home_raw)), teams_in(str(away_raw))
        if len(home) != 1 or len(away) != 1:
            continue
        kickoff = datetime.combine(day.date(), ko).isoformat() if ko else datetime.combine(day.date(), datetime.min.time()).isoformat()
        games.append({"date": day.date().isoformat(), "kickoff": kickoff, "venue": venue or "Unknown", "home": home[0], "away": away[0], "hs": hs, "as": ascore})
    wb.close()
    return sorted(games, key=lambda game: game["kickoff"])


def fixture_for(bet: base.Bet, games: list[dict]) -> dict | None:
    teams, day = set(teams_in(bet.match)), datetime.fromisoformat(bet.date).date()
    candidates = [g for g in games if abs((datetime.fromisoformat(g["date"]).date() - day).days) <= 1 and {g["home"], g["away"]} == teams]
    return candidates[0] if len(candidates) == 1 else None


def form(games: list[dict], game: dict, team: str):
    past = [g for g in games if g["kickoff"] < game["kickoff"] and team in (g["home"], g["away"]) and g["hs"] is not None]
    if not past: return None, None
    prev = past[-1]
    rest = (datetime.fromisoformat(game["date"]).date() - datetime.fromisoformat(prev["date"]).date()).days
    ts, os = (prev["hs"], prev["as"]) if prev["home"] == team else (prev["as"], prev["hs"])
    return rest, "win" if ts > os else "loss" if ts < os else "draw"


def moon(day):
    d = ephem.Date(day.strftime("%Y/%m/%d 12:00:00"))
    new = min(abs(float(d)-float(ephem.previous_new_moon(d))), abs(float(ephem.next_new_moon(d))-float(d)))
    full = min(abs(float(d)-float(ephem.previous_full_moon(d))), abs(float(ephem.next_full_moon(d))-float(d)))
    if new <= 1: return "New Moon (±1 day)"
    if full <= 1: return "Full Moon (±1 day)"
    return None


def rows(game: dict, team: str, games: list[dict]) -> list[str]:
    dt = datetime.fromisoformat(game["kickoff"].replace("Z", "+00:00"))
    # All fixture timestamps are UTC. AEDT runs through early April; AEST thereafter.
    hour = (dt.hour + (11 if dt.month in (1, 2, 3, 4, 10, 11, 12) else 10)) % 24
    rest, last = form(games, game, team)
    out = ["Total Points — Home" if game["home"] == team else "Total Points — Away", "Night Games (kick-off ≥ 18:00)" if hour >= 18 else "Day Games (kick-off < 18:00)"]
    if dt.weekday() in (3, 4): out.append("Thursday / Friday Games")
    elif dt.weekday() == 5: out.append("Saturday Games")
    elif dt.weekday() == 6: out.append("Sunday Games")
    if rest is not None:
        if rest <= 6: out.append("Short Rest (≤ 6 days)")
        elif rest >= 10: out.append("Long Rest (≥ 10 days)")
    if last == "win": out.append("After a Win")
    elif last == "loss": out.append("After a Loss")
    month = {3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October"}.get(dt.month)
    opponent = game['away'] if team == game['home'] else game['home']
    out += [month, moon(dt.date()), f"vs {MATRIX_KEY[opponent]}", game["venue"]]
    return [x for x in out if x]


def wanted(market: str) -> str | None:
    return "unders" if "under" in market.lower() else "overs" if "over" in market.lower() else None


def main() -> None:
    matrix, games = base.load_matrix_xlsx(MATRIX), fixtures()
    records, unmatched = [], []
    for bet in parse_bets():
        direction = wanted(bet.market)
        if not direction: continue
        game = fixture_for(bet, games)
        if not game: unmatched.append(bet); continue
        support, conflict = [], []
        for team in (game["home"], game["away"]):
            for row in rows(game, team, games):
                value = matrix.get(MATRIX_KEY[team], {}).get(row)
                if not value: continue
                edge, raw = value
                (support if raw.startswith(direction) else conflict).append((edge, row, team))
        records.append({"bet":bet, "support":support, "conflict":conflict})
    for record in records:
        record["double"] = sum(x[0] >= MIN_EDGE for x in record["support"]) >= 3 and not any(x[0] >= MIN_EDGE for x in record["conflict"])
    actual = sum(base.pnl(r["bet"]) for r in records)
    qualifying = [r for r in records if r["double"]]
    counterfactual = actual + sum(base.pnl(r["bet"]) for r in qualifying)
    ladder = {t:[r for r in records if sum(x[0] >= t for x in r["support"]) >=3 and not any(x[0] >=t for x in r["conflict"])] for t in (5,10,20,30,40)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "afl_2026_actual_totals_matrix_staking_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w=csv.writer(fh); w.writerow(["id","date","match","market","odds","stake","result","support_5","support_10","support_20","support_30","support_40","conflict_5","qualifies_double","support_rows","conflict_rows"])
        for r in records:
            b=r["bet"]; s=r["support"]; c=r["conflict"]
            w.writerow([b.ident,b.date,b.match,b.market,b.odds,b.stake,b.result,*[sum(x[0]>=t for x in s) for t in (5,10,20,30,40)],sum(x[0]>=5 for x in c),r["double"],"; ".join(f"{x[0]:.1f}% {x[2]} {x[1]}" for x in s),"; ".join(f"{x[0]:.1f}% {x[2]} {x[1]}" for x in c)])
    md_path=OUT_DIR / "afl_2026_actual_totals_matrix_staking_audit.md"
    with md_path.open("w",encoding="utf-8") as fh:
        fh.write("# 2026 AFL actual totals bets — matrix staking audit\n\n")
        fh.write("Frozen matrix: 2022–25 AFL totals matrix. Rule: 3+ aligned signals at the stated threshold, no opposing signal at that threshold; both teams' applicable rows are considered.\n\n")
        fh.write("| Rule | Bets | Wins–losses | Increment if doubled |\n|---|---:|---:|---:|\n")
        for t, rs in ladder.items():
            outcome=Counter(r["bet"].result for r in rs); inc=sum(base.pnl(r["bet"]) for r in rs)
            fh.write(f"| 3+ aligned {t}% signals; no opposing {t}% signal | {len(rs)} | {outcome['win']}–{outcome['loss']} | ${inc:+.2f} |\n")
        fh.write(f"\n## 5% double-stake test\n\n- Eligible totals bets: **{len(records)}**; unmatched: **{len(unmatched)}**.\n- Actual P&L: **${actual:+.2f}**.\n- Qualifiers: **{len(qualifying)}**.\n- Counterfactual P&L: **${counterfactual:+.2f}**.\n- Change from doubling: **${counterfactual-actual:+.2f}**.\n\n")
        fh.write("## Qualifying bets\n\n| Date | Bet | Result | Stake | Supporting signals ≥5% |\n|---|---|---:|---:|---|\n")
        for r in qualifying:
            b=r["bet"]; signals=", ".join(f"{e:.0f}% {row}" for e,row,_ in sorted(r["support"],reverse=True) if e>=5)
            fh.write(f"| {b.date} | {b.market} — {b.match} | {b.result} | ${b.stake:.2f} | {signals} |\n")
        fh.write("\n## Limitation\n\nThis is a small retrospective test. Matrix rows overlap, and alternate totals in one game are correlated; do not treat raw signal counts as independent evidence or use the result alone to alter live staking.\n")
    print(f"Eligible AFL totals: {len(records)} | unmatched: {len(unmatched)} | 5% qualifiers: {len(qualifying)}")
    print(f"Actual P&L: ${actual:+.2f} | counterfactual: ${counterfactual:+.2f} | change: ${counterfactual-actual:+.2f}")
    print(f"Wrote {md_path}\nWrote {csv_path}")

if __name__ == "__main__": main()
