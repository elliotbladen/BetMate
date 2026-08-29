"""Pickle-safe NRL shadow model bundles."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


def margin_to_home_win_probability(margin, residual_scale):
    """Convert an expected home margin into a coherent home-win probability.

    The production margin model stores the out-of-sample standard deviation of
    its margin errors.  Treating those errors as centred normal noise ensures
    the H2H price and fair handicap always describe the same match forecast.
    """
    scale = float(residual_scale)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('residual_scale must be a positive finite number')
    z = np.asarray(margin, dtype=float) / (scale * np.sqrt(2.0))
    # numpy does not expose erf in every supported build, so vectorize math.erf.
    import math
    p = 0.5 * (1.0 + np.vectorize(math.erf, otypes=[float])(z))
    return np.clip(p, .005, .995)


def numeric_frame(X, features):
    frame = pd.DataFrame(X)
    if list(frame.columns) != features:
        if frame.shape[1] != len(features):
            raise ValueError(f'Expected {len(features)} features, received {frame.shape[1]}')
        frame.columns = features
    frame = frame.loc[:, features].copy()
    return frame.apply(pd.to_numeric, errors='coerce')


@dataclass
class MarginShadowBundle:
    feature_names: list[str]
    estimator: object
    trained_through: int
    model_version: str
    residual_scale: float

    @property
    def feature_names_in_(self):
        return np.asarray(self.feature_names, dtype=object)

    def predict(self, X):
        return self.estimator.predict(numeric_frame(X, self.feature_names))


@dataclass
class H2HShadowBundle:
    feature_names: list[str]
    estimator: object
    calibrator: object | None
    trained_through: int
    model_version: str

    @property
    def feature_names_in_(self):
        return np.asarray(self.feature_names, dtype=object)

    def predict_proba(self, X):
        raw = self.estimator.predict_proba(numeric_frame(X, self.feature_names))[:, 1]
        p = self.calibrator.predict_proba(raw.reshape(-1, 1))[:, 1] if self.calibrator else raw
        p = np.clip(p, .005, .995)
        return np.column_stack((1-p, p))

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= .5).astype(int)
