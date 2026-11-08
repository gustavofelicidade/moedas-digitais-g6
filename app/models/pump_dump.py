"""Random Forest pump-start classifier and deterministic alert policy."""

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from app.features.pump_dump import FEATURES
from app.ingestion.pump_dump import MARKET


ALERT = "SUSPECTED_PUMP"
COOLDOWN = pd.Timedelta(minutes=30)


@dataclass
class PumpModel:
    classifier: RandomForestClassifier
    chunk_seconds: int
    threshold: float

    def score(self, features: pd.DataFrame) -> pd.DataFrame:
        result = features.copy()
        result["score"] = self.classifier.predict_proba(result[FEATURES])[:, 1]
        result["status"] = "NO_ALERT"
        candidates = result.loc[result["score"].ge(self.threshold)].sort_values("chunk_end")
        last_alert = {}
        for index, row in candidates.iterrows():
            key = (row["exchange"], row["symbol"])
            close = row["chunk_end"]
            if key in last_alert and close - last_alert[key] < COOLDOWN:
                result.at[index, "status"] = "COOLDOWN"
            else:
                result.at[index, "status"] = ALERT
                last_alert[key] = close
        return result


def train(
    labeled: pd.DataFrame, chunk_seconds: int, test_from: pd.Timestamp, threshold: float
) -> tuple[PumpModel, dict]:
    if not 0 < threshold <= 1:
        raise ValueError("threshold deve ser maior que zero e no máximo 1")
    training = labeled.loc[labeled["chunk_end"].le(test_from)]
    # Includes the source of the first close if it was carried over a quiet bucket.
    test = labeled.loc[labeled["history_start"].ge(test_from)]
    for name, part in [("treino", training), ("teste", test)]:
        if part["label"].nunique() < 2:
            raise ValueError(f"O período de {name} precisa conter janelas positivas e negativas após a separação")

    classifier = RandomForestClassifier(
        n_estimators=200, max_depth=4, min_samples_leaf=6, class_weight="balanced", random_state=42
    )
    classifier.fit(training[FEATURES], training["label"])
    model = PumpModel(classifier, chunk_seconds, threshold)
    scored = model.score(test)
    predicted = scored["status"].eq(ALERT)
    labels = scored["label"]
    return model, {
        "test_from": test_from.isoformat(),
        "threshold": threshold,
        "training_chunks": len(training),
        "training_positives": int(training["label"].sum()),
        "test_chunks": len(test),
        "test_positives": int(labels.sum()),
        "excluded_chunks": len(labeled) - len(training) - len(test),
        "precision": precision_score(labels, predicted, zero_division=0),
        "recall": recall_score(labels, predicted, zero_division=0),
        "f1": f1_score(labels, predicted, zero_division=0),
        "average_precision_before_cooldown": average_precision_score(labels, scored["score"]),
    }
