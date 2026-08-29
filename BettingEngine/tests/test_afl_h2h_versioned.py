import numpy as np
import pandas as pd
import pytest

from ml.afl.h2h_versioned import H2HModelBundle


class ConstantEstimator:
    def predict_proba(self, X):
        p = np.full(len(X), 0.6)
        return np.column_stack((1-p, p))


def test_market_shadow_refuses_missing_market_input():
    model = H2HModelBundle(
        'current_shadow', ['elo_win_prob', 'mkt_home_prob_open'],
        ConstantEstimator(), requires_market=True,
    )
    with pytest.raises(ValueError, match='no ELO fallback'):
        model.predict_proba(pd.DataFrame([{
            'elo_win_prob': .7, 'mkt_home_prob_open': np.nan,
        }]))


def test_market_independent_primary_can_predict_without_market():
    model = H2HModelBundle('legacy_primary', ['elo_win_prob'], ConstantEstimator())
    assert model.predict_proba(pd.DataFrame([{'elo_win_prob': .7}]))[0, 1] == .6
