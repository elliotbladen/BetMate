import unittest
import json
from racing_engine.victorian_200m import parse_csv,parse_graphql

class Victorian200mTest(unittest.TestCase):
    def test_parses_completed_distance_as_distance_to_go(self):
        payload=("date;race\nHORSE ONE;2;200;17.52;0:14.50;400;17.63;0:11.57;1400;16.91;0:12.27\n").encode()
        rows=parse_csv(payload,1400)
        self.assertEqual(rows[0]["runner_number"],2)
        self.assertEqual([x["marker_metres"] for x in rows[0]["points"]],[1200,1000,0])
        self.assertEqual(rows[0]["points"][1]["section_seconds"],11.57)

    def test_rejects_no_content_redirect(self):
        self.assertEqual(parse_csv(b'<meta url="no-content" />',2000),[])

    def test_parses_graphql_split_positions_and_first_partial_segment(self):
        payload={"data":{"getRaceForm":{"raceEntryTimes":[{"horseName":"Via Sistina (IRE)","saddleNumber":7,
            "splitTimes":[{"distance":"2040m-1800m","position":7,"time":"16.66","avgSpeed":14.45},
                          {"distance":"200m-FINISH","position":1,"time":"11.82","avgSpeed":16.92}]}]}}}
        rows=parse_graphql(json.dumps(payload).encode(),2040)
        self.assertEqual(rows[0]["runner_number"],7)
        self.assertEqual(rows[0]["points"][0]["completed_metres"],240)
        self.assertEqual(rows[0]["points"][0]["marker_metres"],1800)
        self.assertEqual(rows[0]["points"][1]["marker_metres"],0)
