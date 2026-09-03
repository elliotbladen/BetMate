import unittest

from ml.football.ucl_draw import validate_draw_graph


def valid_graph():
    clubs = [{"club_id": f"c{i:02d}", "coefficient_pot": i // 9 + 1, "association": f"a{i:02d}"} for i in range(36)]
    fixtures = []
    # A deterministic 4-regular bipartite pot rotation: each club receives
    # two opponents from every pot, with four home and four away overall.
    for pot_a in range(4):
        for pot_b in range(pot_a, 4):
            left = [f"c{i:02d}" for i in range(pot_a * 9, pot_a * 9 + 9)]
            if pot_a == pot_b:
                for i in range(9):
                    fixtures.append({"home_club_id": left[i], "away_club_id": left[(i + 1) % 9]})
                continue
            right = [f"c{i:02d}" for i in range(pot_b * 9, pot_b * 9 + 9)]
            for i in range(9):
                fixtures.append({"home_club_id": left[i], "away_club_id": right[i]})
                fixtures.append({"home_club_id": left[i], "away_club_id": right[(i + 1) % 9]})
    return clubs, fixtures


class UCLDrawTests(unittest.TestCase):
    def test_wrong_team_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "36"):
            validate_draw_graph([], [])

    def test_association_limit_is_enforced(self):
        clubs, fixtures = valid_graph()
        clubs[1]["association"] = clubs[9]["association"] = clubs[10]["association"] = "same"
        with self.assertRaisesRegex(ValueError, "expected eight|association"):
            validate_draw_graph(clubs, fixtures)


if __name__ == "__main__":
    unittest.main()
