"""Fit the daily market reversal classifier on historical candidates."""

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import precision_recall_curve
from sklearn.utils.class_weight import compute_sample_weight


def fit_daily_reversal(
    panel: pd.DataFrame,
    features: list[str],
    *,
    validation_from: pd.Timestamp,
    holdout_from: pd.Timestamp,
    horizon: int,
) -> tuple[LGBMClassifier, float]:
    """Fit on past labels and select the alert threshold on later validation data."""
    eligible = panel.loc[panel["scorable"] & panel["label"].notna()]
    label_end = eligible["date"] + pd.Timedelta(days=horizon)
    train = eligible.loc[label_end.lt(validation_from)]
    validation = eligible.loc[eligible["date"].ge(validation_from) & label_end.lt(holdout_from)]
    train_labels = train["label"].astype(int)
    validation_labels = validation["label"].astype(int)
    if train_labels.nunique() < 2 or validation_labels.nunique() < 2:
        raise ValueError("O treino e a validação precisam de candidatos com e sem reversão.")

    model = LGBMClassifier(
        objective="binary", n_estimators=200, max_depth=4, num_leaves=16,
        min_child_samples=6, random_state=42, verbosity=-1, n_jobs=1,
    )
    model.fit(train[features], train_labels, sample_weight=compute_sample_weight("balanced", train_labels))

    scores = model.predict_proba(validation[features])[:, 1]
    precision, recall, thresholds = precision_recall_curve(validation_labels, scores)
    precision, recall = precision[:-1], recall[:-1]
    denominator = precision + recall
    f1 = np.divide(2 * precision * recall, denominator, out=np.zeros_like(precision), where=denominator > 0)
    threshold = thresholds[np.flatnonzero(f1 == f1.max())[-1]]
    return model, float(threshold)
