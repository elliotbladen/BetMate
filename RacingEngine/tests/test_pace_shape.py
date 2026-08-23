import inspect
import unittest

from racing_engine.pace_shape import _label, _phase_times, build
from racing_engine.sectional_features import derive


class PaceShapeTests(unittest.TestCase):
    def test_clean_nsw_source_has_same_proven_sectional_semantics(self):
        rows=[{"marker_metres":marker,"section_seconds":seconds,"position_at_marker":position}
              for marker,seconds,position in ((600,11.5,4),(400,11.3,3),(200,11.1,2),(0,11.0,1))]
        result=derive("racing-com-nsw-authorised-v2",rows)
        self.assertEqual(result["quality_status"],"ok")
        self.assertAlmostEqual(result["final_400_seconds"],22.1)
        self.assertAlmostEqual(result["final_600_seconds"],33.4)

    def test_nsw_intervals_are_summed_into_three_phases(self):
        rows=[{"marker_metres":marker,"section_seconds":10.0,"position_at_marker":1}
              for marker in (1000,800,600,400,200,0)]
        early,middle,late,reasons=_phase_times("racing-com-nsw-authorised-v2",1200,rows)
        self.assertEqual((early,middle,late),(20.0,20.0,20.0));self.assertEqual(reasons,[])

    def test_long_nsw_race_uses_documented_final_1200_window(self):
        rows=[{"marker_metres":marker,"section_seconds":10.0,"position_at_marker":1}
              for marker in (1000,800,600,400,200,0)]
        early,middle,late,reasons=_phase_times("racing-com-nsw-authorised-v2",1600,rows)
        self.assertEqual((early,middle,late),(20.0,20.0,20.0));self.assertEqual(reasons,[])

    def test_victorian_source_uses_registered_three_phase_semantics(self):
        rows=[{"marker_metres":800,"section_seconds":22.0},{"marker_metres":400,"section_seconds":23.0},{"marker_metres":0,"section_seconds":22.5}]
        self.assertEqual(_phase_times("racing-com-rv-authorised",1200,rows)[:3],(22.0,23.0,22.5))

    def test_continuous_scores_create_expected_archetypes(self):
        self.assertEqual(_label(1.2,.8,-1.0),"pace_collapse")
        self.assertEqual(_label(-1.2,-.3,1.1),"sprint_home")
        self.assertEqual(_label(.8,.7,.2),"sustained_high_pressure")
        self.assertEqual(_label(.1,.1,.1),"even")

    def test_builder_explicitly_uses_prior_only_pars(self):
        source=inspect.getsource(build)
        self.assertIn('"par_method":"strictly_prior_races_only"',source)
        self.assertLess(source.index("sample=exact if"),source.index("exact.append(item)"))


if __name__ == "__main__": unittest.main()
