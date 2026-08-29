import numpy as np
import pandas as pd

from ml.nrl.features import PREMARKET_FEATURES
from ml.nrl.models import (
    H2HShadowBundle,
    MarginShadowBundle,
    margin_to_home_win_probability,
)


class MarginEstimator:
    def predict(self, X):
        return np.full(len(X), 4.5)


class Classifier:
    def predict_proba(self, X):
        p=np.full(len(X),.62)
        return np.column_stack((1-p,p))


def row():
    return pd.DataFrame([{c: np.nan for c in PREMARKET_FEATURES}])


def test_feature_contract_excludes_broken_string_rest_classes():
    assert 'home_rest_class' not in PREMARKET_FEATURES
    assert 'away_rest_class' not in PREMARKET_FEATURES


def test_versioned_bundles_predict_with_missing_optional_inputs():
    margin=MarginShadowBundle(PREMARKET_FEATURES,MarginEstimator(),2025,'test',18.0)
    h2h=H2HShadowBundle(PREMARKET_FEATURES,Classifier(),None,2025,'test')
    assert margin.predict(row())[0] == 4.5
    assert h2h.predict_proba(row())[0,1] == .62


def test_margin_probability_is_coherent_and_symmetric():
    probabilities = margin_to_home_win_probability(np.array([-8.0, 0.0, 8.0]), 18.0)
    assert probabilities[0] < .5 < probabilities[2]
    assert probabilities[1] == .5
    assert np.isclose(probabilities[0] + probabilities[2], 1.0)
