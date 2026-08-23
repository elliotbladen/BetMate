import unittest

from racing_engine.breednet_profiles import parse_profile, slugify


PAGE = '''<div id="HorseHeader"><h1>Scripted <span style="font-size:.8em">(AUS) 2021</span></h1>
<h3>Profile</h3><div class="horse-profile-wrapper"><div class="horse-profile-row">5m Written By (AUS) x Elliptical Orbit (USA) (Scat Daddy (USA))</div>
<div class="horse-profile-row">Foaled Sep 26, 2021</div></div>
<a href="/race-results/Randwick/2026-08-08">Race</a></div>'''


class BreednetProfileTests(unittest.TestCase):
    def test_profile_parses_static_identity_and_race_evidence(self):
        value = parse_profile(PAGE, "https://example.test/horse/scripted")
        self.assertEqual(value["name"], "Scripted")
        self.assertEqual(value["birth_date"], "2021-09-26")
        self.assertEqual(value["sex"], "M")
        self.assertEqual(value["country_code"], "AUS")
        self.assertEqual(value["sire_country_code"], "AUS")
        self.assertEqual(value["race_dates"], ["2026-08-08"])

    def test_slug_is_deterministic(self):
        self.assertEqual(slugify("O'President (NZ)"), "opresident-nz")


if __name__ == "__main__": unittest.main()
