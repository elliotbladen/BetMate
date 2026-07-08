import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "WorldCupEngine"
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_knockout as sk


def test_late_round_pressure_is_zero_early():
    assert sk.late_round_pressure_edge(0, 1800, 1700) == 0.0
    assert sk.late_round_pressure_edge(1, 1800, 1700) == 0.0


def test_late_round_pressure_grows_in_late_rounds():
    qf = sk.late_round_pressure_edge(2, 1800, 1700)
    sf = sk.late_round_pressure_edge(3, 1800, 1700)
    fin = sk.late_round_pressure_edge(4, 1800, 1700)

    assert qf > 0.0
    assert sf > qf
    assert fin > sf


def test_pressure_can_flip_a_close_shootout_edge_in_final_rounds(monkeypatch):
    calls = iter([0.99, 0.53])
    monkeypatch.setattr(sk.random, "random", lambda: next(calls))

    stronger = sk.sample_winner("TeamA", "TeamB", {"TeamA": 1800, "TeamB": 1700}, round_idx=4)
    assert stronger == "TeamA"

    calls = iter([0.99, 0.53])
    monkeypatch.setattr(sk.random, "random", lambda: next(calls))

    earlier = sk.sample_winner("TeamA", "TeamB", {"TeamA": 1800, "TeamB": 1700}, round_idx=0)
    assert earlier == "TeamB"
