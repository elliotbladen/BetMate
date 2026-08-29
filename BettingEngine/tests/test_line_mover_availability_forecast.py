from scripts.line_mover.forecast_availability import miss_probability
from scripts.line_mover.predict_movement import score_projected_availability


def test_confirmed_and_watch_probabilities_are_ordered():
    ruled_out = miss_probability({"notes": "Ruled out - knee"}, 24)
    scans = miss_probability({"notes": "Went for scans on ankle"}, 24)
    probable = miss_probability({"notes": "Available for Round 24"}, 24)
    assert ruled_out > scans > probable


def test_projected_availability_favours_healthier_side():
    forecast = {"teams": {"Home": {"expected_absence_points": 4.0},
                           "Away": {"expected_absence_points": 1.0}}}
    assert score_projected_availability("Home", "Away", forecast) < 0
