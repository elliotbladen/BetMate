import unittest

from racing_engine.form_ranking_research import fit, fit_chronological_cv, loss_and_gradient, probabilities


class FormRankingResearchTests(unittest.TestCase):
    def test_probability_book_is_coherent(self):
        values=probabilities([1.0,2.0,3.0]); self.assertAlmostEqual(sum(values),1.0); self.assertGreater(values[2],values[1])

    def test_training_learns_correct_feature_direction(self):
        races=[]
        for _ in range(40):
            races.append({"features":[{"base":0.0,"peak_gap":1.0},{"base":0.0,"peak_gap":-1.0}],"outcomes":[1,0]})
        fitted=fit(races,("peak_gap",),iterations=300,l2=.05)
        self.assertGreater(fitted["weights"]["peak_gap"],0)
        before,_=loss_and_gradient(races,{"peak_gap":0.0},("peak_gap",),.05)
        self.assertLess(fitted["training_penalized_log_loss"],before)

    def test_regularization_selection_uses_training_subperiods(self):
        races=[]
        for day in range(20):
            races.append({"race_date":f"2024-01-{day+1:02d}","track_slug":"x","race_number":1,
                "features":[{"base":0.0,"peak_gap":1.0},{"base":0.0,"peak_gap":-1.0}],"outcomes":[1,0]})
        fitted=fit_chronological_cv(races,("peak_gap",))
        self.assertIn(fitted["regularization"],(.01,.05,.10,.20)); self.assertEqual(len(fitted["selection_trials"]),4)

if __name__=="__main__": unittest.main()
