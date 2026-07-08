"""
Mythical R32: Japan vs Brazil
ELO updated after R3 results (Japan 1-1 Sweden, Brazil 1-1 Scotland).
No injuries. Neutral venue. T1+T2+T3+T7.
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from elo_ratings import ELO

K = 40

def expected(ra, rb):
    return 1 / (1 + 10 ** ((rb - ra) / 400))

def elo_update(ra, rb, result_a):
    ea = expected(ra, rb)
    return ra + K * (result_a - ea), rb + K * ((1 - result_a) - (1 - ea))

# ── R3 ELO updates ────────────────────────────────────────────────────────
ja_pre, sw_pre = ELO["Japan"], ELO["Sweden"]
ja_new, sw_new = elo_update(ja_pre, sw_pre, 0.5)  # Japan 1-1 Sweden

br_pre, sc_pre = ELO["Brazil"], ELO["Scotland"]
br_new, sc_new = elo_update(br_pre, sc_pre, 0.5)  # Brazil 1-1 Scotland

ja_r32 = round(ja_new)
br_r32 = round(br_new)

print()
print("  R3 ELO updates:")
print("    Japan  {} -> {}  (drew Sweden 1-1)".format(ja_pre, ja_r32))
print("    Brazil {} -> {}  (drew Scotland 1-1)".format(br_pre, br_r32))

# ── Pricing engine ────────────────────────────────────────────────────────
HIGH_PRESS = {"Germany", "England", "Netherlands", "France", "Spain",
              "Portugal", "Belgium", "Norway", "Brazil", "Argentina",
              "Colombia", "USA", "Japan", "South Korea", "Morocco",
              "Croatia", "Scotland", "Switzerland", "Uruguay"}

BASE_GOALS = 1.18
ELO_SCALE  = 0.003
DC_RHO     = -0.13
MAX_GOALS  = 10

def t2_tactical(a, b):
    ha, hb = a in HIGH_PRESS, b in HIGH_PRESS
    if ha and hb:       return 1.04, 1.04
    elif ha and not hb: return 1.02, 0.97
    elif not ha and hb: return 0.97, 1.02
    else:               return 0.99, 0.99

def dc_tau(i, j, lam, mu, rho):
    if i == 0 and j == 0: return max(0, 1 - lam * mu * rho)
    if i == 0 and j == 1: return max(0, 1 + lam * rho)
    if i == 1 and j == 0: return max(0, 1 + mu * rho)
    if i == 1 and j == 1: return max(0, 1 - rho)
    return 1.0

def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def price_game(a, ea, b, eb, form_a=0.0, form_b=0.0, mot_a=0.0, mot_b=0.0):
    diff = ea - eb
    lam  = BASE_GOALS * math.exp( ELO_SCALE * diff / 2)
    mu   = BASE_GOALS * math.exp(-ELO_SCALE * diff / 2)
    ta, tb = t2_tactical(a, b)
    lam *= ta * (1 + form_a) * (1 + mot_a)
    mu  *= tb * (1 + form_b) * (1 + mot_b)

    mat, tot = {}, 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = max(0, poisson_pmf(i, lam) * poisson_pmf(j, mu) * dc_tau(i, j, lam, mu, DC_RHO))
            mat[(i, j)] = p
            tot += p
    mat = {k: v / tot for k, v in mat.items()}

    pa   = sum(p for (i, j), p in mat.items() if i > j)
    pd   = sum(p for (i, j), p in mat.items() if i == j)
    pb   = sum(p for (i, j), p in mat.items() if i < j)
    po25 = sum(p for (i, j), p in mat.items() if i + j >= 3)
    xg   = sum((i + j) * p for (i, j), p in mat.items())

    # Score grid — top 9 scorelines
    top = sorted(mat.items(), key=lambda x: -x[1])[:12]

    # Knockout advancement (90min win + if draw: slight edge to stronger team in ET/pens)
    # Brazil stronger team — estimated 54/46 in pens/ET if it goes to 90min draw
    pen_brazil = 0.54
    pw_japan  = pa + pd * (1 - pen_brazil)
    pw_brazil = pb + pd * pen_brazil

    fo = lambda p: round(1 / p, 2) if p > 0.001 else 99.0

    return {
        "diff": diff, "lam": round(lam, 3), "mu": round(mu, 3), "xg": round(xg, 2),
        "pa": round(pa * 100, 1), "pd": round(pd * 100, 1), "pb": round(pb * 100, 1),
        "oa": fo(pa), "ox": fo(pd), "ob": fo(pb),
        "po25": round(po25 * 100, 1), "oo25": fo(po25), "ou25": fo(1 - po25),
        "pw_a": round(pw_japan * 100, 1), "pw_b": round(pw_brazil * 100, 1),
        "ow_a": fo(pw_japan), "ow_b": fo(pw_brazil),
        "scorelines": top,
    }

# T3: Japan solid (W1 D2, 5pts, held tough opponents)
#     Brazil underwhelming (W1 D2, 5pts, failed to dominate Scotland/Morocco)
# T7: Knockout — both maximum motivation, slight Japan boost (underdog energy)
r = price_game(
    "Japan",  ja_r32,
    "Brazil", br_r32,
    form_a = +0.02,   # Japan consistent, disciplined tournament
    form_b = +0.00,   # Brazil below expected level
    mot_a  = +0.03,   # Underdog knockout energy
    mot_b  = +0.02,   # Knockout focus restored
)

print()
print("=" * 70)
print("  MYTHICAL R32 — Japan vs Brazil")
print("  Neutral venue | No injuries | T1 ELO + T2 Tactical + T3 Form + T7")
print("=" * 70)
print()
print("  Japan ELO:  {}  |  Brazil ELO: {}  |  Diff: {:+d}".format(ja_r32, br_r32, r["diff"]))
print("  xGoals:     Japan {:.3f}  —  Brazil {:.3f}  (xG total: {})".format(r["lam"], r["mu"], r["xg"]))
print()
print("  ── 90-MINUTE RESULT ──────────────────────────────────────────")
print("  Japan win      {:5.1f}%   @  {:5.2f}".format(r["pa"], r["oa"]))
print("  Draw           {:5.1f}%   @  {:5.2f}".format(r["pd"], r["ox"]))
print("  Brazil win     {:5.1f}%   @  {:5.2f}".format(r["pb"], r["ob"]))
print()
print("  ── OVER / UNDER 2.5 GOALS ────────────────────────────────────")
print("  Over 2.5       {:5.1f}%   @  {:5.2f}".format(r["po25"], r["oo25"]))
print("  Under 2.5      {:5.1f}%   @  {:5.2f}  <<<".format(100 - r["po25"], r["ou25"]))
print()
print("  ── KNOCKOUT ADVANCEMENT (inc. ET + pens if 90min draw) ───────")
print("  Japan advance  {:5.1f}%   @  {:5.2f}".format(r["pw_a"], r["ow_a"]))
print("  Brazil advance {:5.1f}%   @  {:5.2f}".format(r["pw_b"], r["ow_b"]))
print()
print("  ── MOST LIKELY SCORELINES ────────────────────────────────────")
print("  {:>7}  {:>8}   |   {:>7}  {:>8}".format("Score", "Prob%", "Score", "Prob%"))
print("  " + "-" * 44)
sc = r["scorelines"]
for idx in range(0, min(12, len(sc)), 2):
    s1, p1 = sc[idx]
    if idx + 1 < len(sc):
        s2, p2 = sc[idx + 1]
        print("  {:>4}-{:<2}   {:>6.2f}%   |   {:>4}-{:<2}   {:>6.2f}%".format(
            s1[0], s1[1], p1*100, s2[0], s2[1], p2*100))
    else:
        print("  {:>4}-{:<2}   {:>6.2f}%".format(s1[0], s1[1], p1*100))
print()
print("  NOTE: Brazil holds ELO advantage ({} vs {}) but R3 form")
print("  NOTE: adjustment closes gap. Japan high-press T2 fires (both")
print("  NOTE: high-press teams -> 1.04x goals each -> slightly open game).")
print("  NOTE: Penalties estimated 54/46 Brazil in ET/pens scenario.")
print()
