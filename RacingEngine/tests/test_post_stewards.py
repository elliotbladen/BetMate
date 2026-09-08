import unittest

from racing_engine.post_stewards import (
    VENUE_CODES,
    clean_report_text,
    paragraphs_to_html,
    parse_races,
)
from racing_engine.stewards import classify_report


SAMPLE = """
STEWARDS’ REPORT
ROYAL RANDWICK RACECOURSE
Saturday 5 September 2026

Supplementary reports:
Race 4: Some Other Meeting 1600m:
Not A Runner - reported to be spelled.

___________________________________________

RACE 1: Midway Handicap 1400m:
Hellfire Express - Began only fairly.

Dusty Bay - Near the 350m made contact with Long Legs.
20260905RR 2

Long Legs - Near the 350m was bumped by Dusty Bay, which shifted out.

RACE 2: TAB Highway Handicap 1200m:
Decorum – Held up from the 400m until approaching the 300m.

Put To The Sword (NZ) - Slow to begin.

King’s Secret - Raced wide without cover throughout.

RACE 8: Concorde Stakes 1000m
Headwall - Began only fairly. Unable to be fully tested near the 100m.

GENERAL:
Swab samples were taken from all winners.
"""


class ParseRacesTests(unittest.TestCase):
    def setUp(self):
        self.races = parse_races(SAMPLE)
        self.by_number = {race["race_number"]: race for race in self.races}

    def test_only_numbered_race_blocks_are_returned(self):
        self.assertEqual([1, 2, 8], [race["race_number"] for race in self.races])

    def test_header_without_trailing_colon_is_recognised(self):
        self.assertEqual("Concorde Stakes", self.by_number[8]["race_name"])
        self.assertEqual(1000, self.by_number[8]["distance_metres"])

    def test_supplementary_and_general_sections_are_excluded(self):
        joined = " ".join(p for race in self.races for p in race["paragraphs"])
        self.assertNotIn("Not A Runner", joined)
        self.assertNotIn("Swab samples", joined)

    def test_page_stamp_is_stripped_from_a_paragraph_boundary(self):
        paragraphs = self.by_number[1]["paragraphs"]
        self.assertEqual(3, len(paragraphs))
        self.assertTrue(paragraphs[1].startswith("Dusty Bay - "))
        self.assertNotIn("20260905RR", " ".join(paragraphs))

    def test_dash_and_curly_apostrophe_paragraphs_split_and_attribute(self):
        paragraphs = self.by_number[2]["paragraphs"]
        self.assertEqual(3, len(paragraphs))
        events = classify_report(paragraphs_to_html(paragraphs),
                                 ["Decorum", "Put To The Sword", "King's Secret"])
        by_horse = {event["horse_name"]: event["category"] for event in events}
        self.assertEqual("held_up", by_horse["Decorum"])
        self.assertEqual("slow_start", by_horse["Put To The Sword"])
        self.assertEqual("wide_no_cover", by_horse["King's Secret"])

    def test_clean_report_text_folds_punctuation(self):
        cleaned = clean_report_text("Decorum – Held. King’s Secret")
        self.assertIn("Decorum - Held", cleaned)
        self.assertIn("King's Secret", cleaned)

    def test_no_races_returns_empty_list(self):
        self.assertEqual([], parse_races("just some prose with no race headers"))

    def test_sydney_metro_codes_are_configured(self):
        self.assertEqual(("RAND",), VENUE_CODES["randwick"])
        self.assertIn("RHIL", VENUE_CODES["rosehill"])


if __name__ == "__main__":
    unittest.main()
