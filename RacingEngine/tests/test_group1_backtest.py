import unittest

from racing_engine.group1_backtest import model_quote,qualifies,roi_interval,settle_market


class Group1BacktestTests(unittest.TestCase):
    def test_110_percent_book_quote(self):
        self.assertAlmostEqual(model_quote(0.20),1/(0.20*1.10))

    def test_edge_is_strictly_greater_than_ten_percent(self):
        quote=5.0
        self.assertFalse(qualifies(5.5,quote))
        self.assertTrue(qualifies(5.51,quote))

    def test_commission_applies_to_net_market_profit(self):
        bets=[{"close_price":5.0,"won":True},{"close_price":20.0,"won":False}]
        gross,net=settle_market(bets,0.10)
        self.assertEqual(gross,3.0)
        self.assertAlmostEqual(net,2.7)

    def test_roi_interval_is_deterministic(self):
        races=[{"bet_count":1,"net_pnl":1.0},{"bet_count":1,"net_pnl":-1.0}]
        self.assertEqual(roi_interval(races,100),roi_interval(races,100))


if __name__=="__main__":unittest.main()
