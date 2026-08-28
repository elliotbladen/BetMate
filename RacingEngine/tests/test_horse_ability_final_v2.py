import unittest

from racing_engine.horse_ability_final_v2 import final_decision


def comparison(delta=-0.01,upper=-0.001):
    return {"log_loss_delta":delta,"paired_log_loss_interval":{"upper":upper}}


class HorseAbilityFinalV2Tests(unittest.TestCase):
    def test_uncertain_v1_result_freezes_research_model(self):
        period={f"candidate_vs_{name}":comparison() for name in ("rejected_v2","v1","uniform")}
        evaluation={"validation":period,"historical_holdout":period}
        evaluation["validation"]["candidate_vs_v1"]=comparison(upper=0.001)
        decision,reasons=final_decision(evaluation,{"named":True})
        self.assertEqual(decision,"FINAL_RESEARCH_FREEZE")
        self.assertIn("validation uncertainty versus V1 includes zero",reasons)

    def test_all_gates_can_promote(self):
        period={f"candidate_vs_{name}":comparison() for name in ("rejected_v2","v1","uniform")}
        decision,reasons=final_decision({"validation":period,"historical_holdout":period},{"named":True})
        self.assertEqual(decision,"PRODUCTION_PROMOTION_ELIGIBLE")
        self.assertEqual(reasons,[])


if __name__=="__main__":unittest.main()
