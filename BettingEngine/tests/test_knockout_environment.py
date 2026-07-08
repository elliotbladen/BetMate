import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "WorldCupEngine"
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_knockout as sk


def test_mexico_city_environment_scales_total_xg_and_host_share():
    _, lam_neutral, mu_neutral = sk.build_score_matrix(
        sk.ELO["Mexico"], sk.ELO["Ecuador"], "Mexico", "Ecuador"
    )
    _, lam_env, mu_env = sk.build_score_matrix(
        sk.ELO["Mexico"], sk.ELO["Ecuador"], "Mexico", "Ecuador", venue="Mexico City Stadium"
    )

    assert lam_env + mu_env < lam_neutral + mu_neutral
    assert lam_env / (lam_env + mu_env) > lam_neutral / (lam_neutral + mu_neutral)
