import unittest
from racing_engine.energy_sectionals import _band,_fit,_phase_speeds,_segments,_rich_segments


class EnergySectionalTests(unittest.TestCase):
    def test_rich_segments_preserve_partial_opening_and_actual_positions(self):
        rows=[{"marker_metres":1800,"section_seconds":16.0,"position_at_marker":5},
              {"marker_metres":1600,"section_seconds":12.0,"position_at_marker":3}]
        segments=_rich_segments(2040,rows)
        self.assertAlmostEqual(segments[0][1],15.0)
        self.assertEqual(segments[0][3],5)
        self.assertAlmostEqual(segments[1][1],200/12)

    def test_distance_bands(self):
        self.assertEqual(_band(1400),"sprint")
        self.assertEqual(_band(1600),"middle")
        self.assertEqual(_band(2400),"staying")

    def test_nsw_consecutive_200m_velocity(self):
        rows=[{"marker_metres":m,"section_seconds":10.0,"position_at_marker":1} for m in (1000,800,600,400,200,0)]
        segments=_segments("racing-com-nsw-authorised-v2",1200,rows)
        self.assertEqual(len(segments),6)
        self.assertTrue(all(abs(row[1]-20)<1e-9 for row in segments))
        self.assertTrue(all(value is not None for value in _phase_speeds(segments).values()))

    def test_victorian_opening_segment_uses_distance_to_800(self):
        rows=[{"marker_metres":800,"section_seconds":20.0,"position_at_marker":1},
              {"marker_metres":400,"section_seconds":20.0,"position_at_marker":1},
              {"marker_metres":0,"section_seconds":20.0,"position_at_marker":1}]
        segments=_segments("racing-com-rv-authorised",1200,rows)
        self.assertTrue(all(abs(row[1]-20)<1e-9 for row in segments))

    def test_sparse_fit_is_frozen_at_zero(self):
        result=_fit([],('achievement','compensation'))
        self.assertEqual(result['status'],'insufficient_sample_frozen_zero')
        self.assertEqual(result['compensation'],0)

if __name__=="__main__":unittest.main()
