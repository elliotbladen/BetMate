from scripts.line_mover.predict_movement import (
    _selection_name_matches,
    score_injury_differential,
)


def test_initial_name_matches_full_injury_name():
    assert _selection_name_matches("M Bontempelli", "Marcus Bontempelli")
    assert _selection_name_matches("N W-Milera", "Nasiah Wanganeen-Milera")
    assert not _selection_name_matches("J Martin", "Nic Martin")


def test_verified_injuries_ignore_omitted_players_and_credit_return():
    lists = {"teams": {
        "Home": {"ins": ["A Return"], "outs": ["O Omitted", "I Injured"]},
        "Away": {"ins": [], "outs": ["A Hurt"]},
    }}
    injuries = [
        {"team": "Home", "player": "Isaac Injured"},
        {"team": "Home", "player": "Adam Return"},
        {"team": "Away", "player": "Aaron Hurt"},
    ]
    # Home: one injury out minus one returning in = 0. Away: one injury out.
    assert score_injury_differential("Home", "Away", lists, injuries) == 0.2
