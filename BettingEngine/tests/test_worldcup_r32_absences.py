import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "WorldCupEngine"
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "scripts"))

from r32_team_data import ATTACK_ABSENCES, DEFENCE_ABSENCES
import simulate_knockout as sk


def test_australia_absences_are_loaded():
    assert "Australia" in ATTACK_ABSENCES
    assert "Australia" in DEFENCE_ABSENCES
    assert ATTACK_ABSENCES["Australia"] < 0
    assert DEFENCE_ABSENCES["Australia"] > 0


def test_absence_changes_australia_egypt_prices():
    attack_original = ATTACK_ABSENCES.get("Australia", 0.0)
    defence_original = DEFENCE_ABSENCES.get("Australia", 0.0)
    try:
        _, lam_with, mu_with = sk.build_score_matrix(sk.ELO["Australia"], sk.ELO["Egypt"], "Australia", "Egypt")
        ATTACK_ABSENCES["Australia"] = 0.0
        DEFENCE_ABSENCES["Australia"] = 0.0
        _, lam_without, mu_without = sk.build_score_matrix(sk.ELO["Australia"], sk.ELO["Egypt"], "Australia", "Egypt")
    finally:
        ATTACK_ABSENCES["Australia"] = attack_original
        DEFENCE_ABSENCES["Australia"] = defence_original

    assert lam_with < lam_without
    assert mu_with > mu_without
