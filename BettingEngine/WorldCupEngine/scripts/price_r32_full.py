"""
FIFA World Cup 2026 — Round of 32 full pricing report.

Uses the existing knockout engine:
T1 ELO | T2 Tactical | T3 Group-stage form from ELO notes | T4 Environment
| T5 Absences | T7 Knockout motivation | T8 Bracket path.

Output:
    WorldCupEngine/outputs/r32_full_pricing.md
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
sys.path.insert(0, str(DATA))

from elo_ratings import ELO
from r32_team_data import ATTACK_ABSENCES, DEFENCE_ABSENCES, ABSENCE_NOTES
from simulate_knockout import (
    BASE_GOALS,
    DC_RHO,
    ELO_SCALE,
    HIGH_PRESS,
    MAX_GOALS,
    build_score_matrix,
    run_simulation,
    t2_tactical,
)
from knockout_context import VENUE_CONTEXT

R32_FIXTURES = [
    ("Canada", "South Africa", "Canada 1-0 South Africa already played"),
    ("Brazil", "Japan", "Houston Stadium"),
    ("Germany", "Paraguay", "Boston Stadium"),
    ("Netherlands", "Morocco", "Monterrey Stadium"),
    ("Ivory Coast", "Norway", "Dallas Stadium"),
    ("France", "Sweden", "New York/New Jersey Stadium"),
    ("Mexico", "Ecuador", "Mexico City Stadium"),
    ("England", "DR Congo", "Atlanta Stadium"),
    ("Belgium", "Senegal", "Seattle Stadium"),
    ("USA", "Bosnia-Herzegovina", "San Francisco Bay Stadium"),
    ("Spain", "Austria", "Los Angeles Stadium"),
    ("Portugal", "Croatia", "Toronto Stadium"),
    ("Switzerland", "Algeria", "BC Place Vancouver"),
    ("Australia", "Egypt", "Dallas Stadium"),
    ("Argentina", "Cabo Verde", "Miami Stadium"),
    ("Colombia", "Ghana", "Kansas City Stadium"),
]

TEAM_FORM = {
    "Germany": "+ group control, 7-1 opener and 2-1 v Ivory Coast",
    "Scotland": "+ upset Brazil in R3, confidence spike",
    "France": "+ 6 pts through R2, clean attacking profile",
    "Sweden": "+ beat Japan in R3 after Netherlands setback",
    "South Korea": "+ qualified out of Mexico group, competitive",
    "Switzerland": "+ unbeaten through R2, strong control",
    "Netherlands": "+ recovered after Japan draw, high ceiling",
    "Morocco": "+ topped Brazil/Scotland group, strong tournament form",
    "DR Congo": "neutral, Colombia R2 result was estimated in data",
    "Ghana": "+ unbeaten through R2, drew England",
    "Spain": "+ elite baseline but Cape Verde draw trims ceiling",
    "Austria": "neutral, handled Jordan then lost to Argentina",
    "USA": "++ 6 pts through R2, strong scoring form",
    "Algeria": "neutral, alive after Jordan win",
    "Egypt": "- R3 Iran result estimated as loss",
    "Czechia": "neutral, estimated final slot",
    "Brazil": "- R3 Scotland loss baked into ELO",
    "Japan": "- R3 Sweden loss, still high tactical floor",
    "Ivory Coast": "+ beat Ecuador, competitive vs Germany",
    "Norway": "++ 6 pts through R2, strong scoring form",
    "Mexico": "++ 6 pts through R2, strong scoring form",
    "Cabo Verde": "+ Spain/Uruguay draws, spoiler profile",
    "England": "+ 4 pts through R2, Ghana draw trims rating",
    "Portugal": "neutral, DRC draw then Uzbekistan rout",
    "Argentina": "++ 6 pts through R2, best bracket seed",
    "Uruguay": "- two draws through R2, not firing yet",
    "Iran": "+ estimated group winner from Egypt result",
    "Australia": "neutral, beat Turkey then lost to USA",
    "Canada": "++ host, 6-0 Qatar in group-stage profile",
    "Belgium": "- bracket/data conflict: engine has Belgium in R32 despite notes saying eliminated",
    "Colombia": "+ estimated 6 pts through R2",
    "Paraguay": "neutral, rebounded after USA loss",
    "Ecuador": "+ beat Germany in R3 per verified R32 schedule implications",
    "Bosnia-Herzegovina": "neutral, qualified from Canada/Swiss group",
    "Senegal": "neutral, survived France/Norway group",
    "Croatia": "neutral, recovered after England loss",
    "South Africa": "eliminated by Canada 1-0 in R32",
}

DATA_RISK_NOTES = {
    "Belgium": "data conflict needs manual confirmation",
    "Czechia": "estimated slot, verify before betting",
    "DR Congo": "Colombia group result estimated in engine",
    "Iran": "Egypt R3 result estimated in engine",
}


def fair_odd(p):
    return round(1 / p, 2) if p > 0.001 else 99.0


def asian_line(xg_diff):
    fav = abs(xg_diff)
    if fav < 0.12:
        return "Pick"
    if fav < 0.32:
        return "-0.25"
    if fav < 0.52:
        return "-0.5"
    if fav < 0.72:
        return "-0.75"
    if fav < 0.95:
        return "-1"
    if fav < 1.20:
        return "-1.25"
    return "-1.5"


def total_line(xg_total):
    if xg_total < 2.15:
        return "2.0/2.25"
    if xg_total < 2.38:
        return "2.25"
    if xg_total < 2.62:
        return "2.5"
    if xg_total < 2.85:
        return "2.5/2.75"
    return "2.75"


def tier_text(a, b, lam, mu, pa, pd, pb, qa, qb, p_o25, venue_note):
    ea, eb = ELO[a], ELO[b]
    ta, tb = t2_tactical(a, b)
    t1 = f"T1 ELO: {a} {ea}, {b} {eb}, diff {ea-eb:+d}."
    t2 = f"T2 Tactical: {a} {'high press' if a in HIGH_PRESS else 'low/mid block'} x{ta:.2f}; {b} {'high press' if b in HIGH_PRESS else 'low/mid block'} x{tb:.2f}."
    t3 = f"T3 Form: {a} {TEAM_FORM.get(a, 'neutral')}; {b} {TEAM_FORM.get(b, 'neutral')}."
    def env_text(team: str, venue: str) -> str:
        profile = VENUE_CONTEXT.get(venue, {})
        bits = []
        if profile.get("altitude_m", 0):
            bits.append(f"altitude {profile['altitude_m']}m")
        if profile.get("host_team") == team:
            bits.append("host acclimatisation")
        return ", ".join(bits) if bits else "neutral environment"

    t4 = f"T4 Environment: {a} {env_text(a, venue_note)}; {b} {env_text(b, venue_note)}."
    def abs_text(team: str) -> str:
        parts = []
        if team in ATTACK_ABSENCES:
            parts.append(f"attack {ATTACK_ABSENCES[team]:+.0%}")
        if team in DEFENCE_ABSENCES:
            parts.append(f"defence {DEFENCE_ABSENCES[team]:+.0%}")
        if not parts:
            return DATA_RISK_NOTES.get(team, "no confirmed absence adjustment loaded")
        note = DATA_RISK_NOTES.get(team)
        return ", ".join(parts) + (f" ({note})" if note else "")

    t5 = f"T5 Absences/data risk: {a}: {abs_text(a)}; {b}: {abs_text(b)}."
    t6 = "T6 Recovery: neutral in the remaining R32 slate; active later if a team has extra-time fatigue or a short-turnaround path."
    t7 = "T7 Knockout: draw mass is high; to-qualify price uses ELO-weighted ET/pens."
    t8 = f"T8 Market shape: xG {a} {lam:.2f} - {b} {mu:.2f}; 90m {pa*100:.1f}/{pd*100:.1f}/{pb*100:.1f}; qualify {qa*100:.1f}/{qb*100:.1f}; O2.5 {p_o25*100:.1f}%."
    return [t1, t2, t3, t4, t5, t6, t7, t8]


def price_match(a, b):
    venue_note = next((v for x, y, v in R32_FIXTURES if x == a and y == b), None)
    mat, lam, mu = build_score_matrix(ELO[a], ELO[b], a, b, venue=venue_note)
    pa = sum(p for (i, j), p in mat.items() if i > j)
    pd = sum(p for (i, j), p in mat.items() if i == j)
    pb = sum(p for (i, j), p in mat.items() if i < j)
    p_o25 = sum(p for (i, j), p in mat.items() if i + j >= 3)
    xg_total = sum((i + j) * p for (i, j), p in mat.items())
    xg_diff = lam - mu
    pen_a = max(0.35, min(0.65, 0.5 + (ELO[a] - ELO[b]) / 4000))
    qa = pa + pd * pen_a
    qb = pb + pd * (1 - pen_a)
    scores = sorted(mat.items(), key=lambda x: -x[1])[:5]
    fav = a if qa >= qb else b
    fav_line = asian_line(xg_diff)
    if fav == b and fav_line != "Pick":
        fav_line = f"{b} {fav_line}"
    elif fav_line != "Pick":
        fav_line = f"{a} {fav_line}"
    return {
        "a": a,
        "b": b,
        "lam": lam,
        "mu": mu,
        "pa": pa,
        "pd": pd,
        "pb": pb,
        "qa": qa,
        "qb": qb,
        "p_o25": p_o25,
        "xg_total": xg_total,
        "line": fav_line,
        "total_line": total_line(xg_total),
        "scores": scores,
        "tiers": tier_text(a, b, lam, mu, pa, pd, pb, qa, qb, p_o25, venue_note),
    }


def main():
    OUT.mkdir(exist_ok=True)
    matches = [price_match(a, b) for a, b, _ in R32_FIXTURES]

    lines = []
    lines.append("# World Cup 2026 R32 Full Pricing")
    lines.append("")
    lines.append("Model: Dixon-Coles Poisson from ELO, tactical multipliers, verified R32 fixture list, host/venue note where relevant, ELO-weighted ET/pens for to-qualify.")
    lines.append("")
    lines.append("Fixture source: SB Nation R32 schedule updated Jun 28, 2026.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Game | 90m fair 1-X-2 | To qualify | Fair line | Total | Read |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for m, (_, _, venue_note) in zip(matches, R32_FIXTURES):
        read = "Under" if m["p_o25"] < 0.45 else "Over" if m["p_o25"] > 0.55 else "No total edge"
        lines.append(
            f"| {m['a']} v {m['b']} | {fair_odd(m['pa'])} / {fair_odd(m['pd'])} / {fair_odd(m['pb'])} "
            f"| {m['a']} {fair_odd(m['qa'])}; {m['b']} {fair_odd(m['qb'])} "
            f"| {m['line']} | {m['total_line']} | {read}; {venue_note} |"
        )

    lines.append("")
    lines.append("## Full Tiers")
    for idx, (m, (_, _, venue_note)) in enumerate(zip(matches, R32_FIXTURES), 1):
        lines.append("")
        lines.append(f"### {idx}. {m['a']} v {m['b']}")
        lines.append("")
        lines.append(
            f"Fair: 90m {m['a']} {fair_odd(m['pa'])}, Draw {fair_odd(m['pd'])}, {m['b']} {fair_odd(m['pb'])}. "
            f"To qualify: {m['a']} {fair_odd(m['qa'])}, {m['b']} {fair_odd(m['qb'])}. "
            f"xG {m['lam']:.2f}-{m['mu']:.2f}; total {m['xg_total']:.2f}; line {m['line']}; total {m['total_line']}."
        )
        lines.append("")
        lines.append("Most likely scores: " + ", ".join(f"{s[0]}-{s[1]} ({p*100:.1f}%)" for s, p in m["scores"]) + ".")
        lines.append("")
        for t in m["tiers"]:
            lines.append(f"- {t}")
        lines.append(f"- Venue/source note: {venue_note}.")

    out_path = OUT / "r32_full_pricing.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
