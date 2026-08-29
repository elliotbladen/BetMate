"""Versioned AFL H2H models and time-safe calibration helpers."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


@dataclass
class H2HModelBundle:
    """Pickle-safe deploy wrapper carrying its feature/data contract."""

    name: str
    feature_names: list[str]
    estimator: object
    calibrator: IsotonicRegression | None = None
    requires_market: bool = False
    trained_through: int | None = None

    @property
    def feature_names_in_(self):
        return np.asarray(self.feature_names, dtype=object)

    def predict_proba(self, X):
        frame = pd.DataFrame(X).loc[:, self.feature_names].apply(
            pd.to_numeric, errors='coerce'
        )
        if self.requires_market and frame['mkt_home_prob_open'].isna().any():
            raise ValueError(
                f'{self.name} requires a real mkt_home_prob_open; no ELO fallback is allowed'
            )
        raw = self.estimator.predict_proba(frame.fillna(0))[:, 1]
        prob = self.calibrator.predict(raw) if self.calibrator is not None else raw
        prob = np.clip(prob, 0.001, 0.999)
        return np.column_stack((1.0 - prob, prob))

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)
