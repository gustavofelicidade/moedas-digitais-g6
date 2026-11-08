import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from lightgbm import LGBMClassifier

from app.agent.pump_dump import build_pump_agent
from app.features.pump_dump import build_features, label_features
from app.ingestion.pump_dump import read_events, read_trades
from app.models.pump_dump import ALERT, PumpModel, train


class PumpDumpTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.trades = Path(temp.name) / "trades.csv"
        self.events = Path(temp.name) / "events.csv"
        self.start = pd.Timestamp("2024-01-01T00:00:00Z")
        self.cutoff = self.start + pd.Timedelta(days=1)
        records = []
        events = []
        for day in (self.start, self.cutoff):
            segment = day.date().isoformat()
            for second in range(0, 3601, 5):
                timestamp = day + pd.Timedelta(seconds=second)
                records.append(["example", "ABC/BTC", timestamp, 1, 1, "buy", segment])
                if second == 3300:
                    events.append(["example", "ABC/BTC", timestamp])
                    records.extend([
                        ["example", "ABC/BTC", timestamp, 2, 100, "buy", segment],
                        ["example", "ABC/BTC", timestamp, 3, 100, "buy", segment],
                    ])
        pd.DataFrame(records, columns=[
            "exchange", "symbol", "timestamp", "price", "quantity", "side", "segment",
        ]).to_csv(self.trades, index=False)
        pd.DataFrame(events, columns=["exchange", "symbol", "timestamp"]).to_csv(self.events, index=False)

    def test_event_boundary_and_causal_features(self):
        trades = read_trades(self.trades)
        events = read_events(self.events)
        features = build_features(trades, 5)
        labeled = label_features(features, events, 5)
        positives = labeled.loc[labeled["label"].eq(1)]
        self.assertEqual(positives["chunk_start"].tolist(), events["timestamp"].tolist())
        self.assertAlmostEqual(positives.iloc[0]["avg_rush_orders"], 1 / 600)
        previous = labeled.loc[labeled["chunk_end"].eq(events.iloc[0]["timestamp"])].iloc[0]
        self.assertEqual(previous["avg_rush_orders"], 0)
        self.assertEqual(previous["label"], 0)
        self.assertNotIn(trades["timestamp"].max(), labeled["chunk_start"].tolist())
        events.loc[0, "exchange"] = "other"
        with self.assertRaisesRegex(ValueError, "sem cobertura"):
            label_features(features, events, 5)

    def test_training_and_agent_use_the_same_features(self):
        features = build_features(read_trades(self.trades), 5)
        labeled = label_features(features, read_events(self.events), 5)
        cutoff = self.cutoff + pd.Timedelta(seconds=30)
        model, metrics = train(labeled, 5, cutoff, 0.5)
        self.assertIsInstance(model.classifier, LGBMClassifier)
        self.assertEqual(metrics["training_positives"], 1)
        self.assertEqual(metrics["test_positives"], 1)
        self.assertEqual(metrics["excluded_chunks"], 6)
        scored = build_pump_agent(model).invoke({"trades_path": str(self.trades)})["detections"]
        pd.testing.assert_series_equal(scored["score"], model.score(features)["score"])

    def test_cooldown_uses_market_and_allows_exactly_thirty_minutes(self):
        features = build_features(read_trades(self.trades), 5).iloc[:4].copy()
        features["chunk_end"] = pd.to_datetime([
            "2024-01-01T01:00:00Z", "2024-01-01T01:01:00Z",
            "2024-01-01T01:02:00Z", "2024-01-01T01:30:00Z",
        ])
        features.loc[2, "exchange"] = "other"
        classifier = Mock()
        classifier.predict_proba.return_value = pd.DataFrame([[0.1, 0.9]] * 4).to_numpy()
        result = PumpModel(classifier, 5, 0.5).score(features)
        self.assertEqual(result["status"].tolist(), [ALERT, "COOLDOWN", ALERT, ALERT])


if __name__ == "__main__":
    unittest.main()
