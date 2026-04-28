import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class TimeFeatures(BaseEstimator, TransformerMixin):
    """Extracts hour-of-day and time-of-day bucket from the 'Time' column (seconds since first tx)."""

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        X["hour"] = (X["Time"] // 3600) % 24
        X["time_bucket"] = pd.cut(
            X["hour"],
            bins=[0, 6, 12, 18, 24],
            labels=["dawn", "morning", "afternoon", "night"],
            right=False,
        ).astype(str)
        return X


class AmountFeatures(BaseEstimator, TransformerMixin):
    """Log-transforms Amount and creates amount quintile buckets."""

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        X["log_amount"] = np.log1p(X["Amount"])
        X["amount_bucket"] = pd.qcut(
            X["Amount"], q=5, labels=["xs", "s", "m", "l", "xl"], duplicates="drop"
        ).astype(str)
        return X


class DropRawColumns(BaseEstimator, TransformerMixin):
    def __init__(self, cols: list):
        self.cols = cols

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.drop(columns=[c for c in self.cols if c in X.columns])


def build_feature_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("time_feats", TimeFeatures()),
            ("amount_feats", AmountFeatures()),
            ("drop_raw", DropRawColumns(cols=["Time", "Amount", "time_bucket", "amount_bucket"])),
            ("scaler", StandardScaler()),
        ]
    )


def get_feature_names(df: pd.DataFrame) -> list:
    """Returns feature column names after pipeline transformation (excluding target)."""
    return [c for c in df.columns if c != "Class"]
