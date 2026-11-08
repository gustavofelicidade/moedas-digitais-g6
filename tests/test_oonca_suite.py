"""Unit tests for OONCA Behavioral Features, Risk Policy, Audit Trail, and Visual Dashboard."""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from app.agent.graph import analyze, batch_analyze
from app.audit.trail import append_audit_log, build_audit_record
from app.features.wallet_behavior import compute_wallet_features
from app.ingestion.repository import WalletRepository
from app.ingestion.schema import ProposedOperation
from app.models.risk import RiskPolicy, assess
from app.visualization.risk import plot_assessment, plot_operator_dashboard


SENDER = "0xc2d7cf95645d33006175b78989035c7c9061d3f9"
RECIP_KNOWN = "0x002f0c8119c16d310342d869ca8bf6ace34d9c39"
RECIP_CONTRACT = "0x1111111111111111111111111111111111111111"
RECIP_UNKNOWN = "0x9999999999999999999999999999999999999999"


class TestOoncaSuite(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.tx_path = self.root / "first_order_df.csv"
        self.meta_path = self.root / "wallet_metadata.csv"

        # Build >= 22 unique historical transactions with rapid-fire cadence (<=60s) and known recipient
        base_ts = 1514764800  # 2018-01-01T00:00:00Z
        rows = []
        for i in range(22):
            rows.append({
                "Unnamed: 0": i,
                "TxHash": f"0xhash_{i}",
                "BlockHeight": 4800000 + i,
                "TimeStamp": base_ts + i * 20,  # 20s apart -> rapid fire!
                "From": SENDER,
                "To": RECIP_KNOWN if i < 18 else RECIP_CONTRACT,
                "Value": 1.0 if i < 20 else 5.0,
                "isError": 0,
            })
        # Add a duplicate TxHash row to test duplicate_row_ratio
        rows.append({
            "Unnamed: 0": 99,
            "TxHash": "0xhash_0",
            "BlockHeight": 4800000,
            "TimeStamp": base_ts,
            "From": SENDER,
            "To": RECIP_KNOWN,
            "Value": 1.0,
            "isError": 0,
        })
        pd.DataFrame(rows).to_csv(self.tx_path, index=False)

        meta_rows = [
            {
                "wallet_address": SENDER,
                "wallet_type": "eoa",
                "ens_name": None,
                "ens_location": None,
                "contract_code_bytes": "0",
                "lookup_status": "ok",
                "observed_at": "2026-11-07T00:00:00Z",
            },
            {
                "wallet_address": RECIP_KNOWN,
                "wallet_type": "eoa",
                "ens_name": "treasury.eth",
                "ens_location": None,
                "contract_code_bytes": "0",
                "lookup_status": "ok",
                "observed_at": "2026-11-07T00:00:00Z",
            },
            {
                "wallet_address": RECIP_CONTRACT,
                "wallet_type": "contract",
                "ens_name": None,
                "ens_location": None,
                "contract_code_bytes": "4096",
                "lookup_status": "ok",
                "observed_at": "2026-11-07T00:00:00Z",
            },
        ]
        pd.DataFrame(meta_rows).to_csv(self.meta_path, index=False)
        self.repo = WalletRepository(tx_path=self.tx_path, metadata_path=self.meta_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compute_wallet_features_and_automation_proxy(self):
        df = pd.read_csv(self.tx_path)
        feats = compute_wallet_features(df, SENDER, RECIP_KNOWN, min_error_obs=20)
        self.assertEqual(feats["n_rows"], 23)
        self.assertEqual(feats["n_unique_tx_hashes"], 22)
        self.assertGreater(feats["duplicate_row_ratio"], 0.0)
        self.assertTrue(feats["recipient_seen"])
        self.assertEqual(feats["recipient_tx_count"], 19)
        self.assertTrue(feats["error_rate_reliable"])
        self.assertGreater(feats["recipient_hhi"], 0.5)
        self.assertTrue(feats["automation_proxy"]["flagged"])
        self.assertEqual(
            feats["automation_proxy"]["disclaimer"],
            "behavioral_proxy_not_ai_proof",
        )

    def test_repository_profile_includes_recipient_metadata(self):
        prof = self.repo.profile(SENDER, RECIP_CONTRACT)
        self.assertIsNotNone(prof["wallet_metadata"])
        self.assertIsNotNone(prof["recipient_metadata"])
        self.assertEqual(prof["recipient_metadata"]["wallet_type"], "contract")

    def test_risk_assessment_rules_and_counterfactuals(self):
        prof = self.repo.profile(SENDER, RECIP_UNKNOWN)
        op = ProposedOperation.from_values(
            wallet_from=SENDER,
            wallet_to=RECIP_UNKNOWN,
            amount="15.0",
            operator_id="op_test",
        )
        res = assess(op.as_state(), prof, RiskPolicy(max_amount_eth=Decimal("10.0")))
        self.assertEqual(res["decision"], "BLOCK")
        self.assertEqual(res["risk_score"], 100)
        self.assertTrue(any(r["rule_id"] == "policy_max_amount_eth" and r["triggered"] for r in res["rule_breakdown"]))
        self.assertTrue(any(r["rule_id"] == "recipient_novelty" and r["triggered"] for r in res["rule_breakdown"]))
        self.assertGreater(len(res["counterfactuals"]), 0)
        self.assertIn("recipient_metadata_missing", res["missing_data_flags"])

    def test_agent_graph_audit_and_jsonl_persistence(self):
        op = ProposedOperation.from_values(
            wallet_from=SENDER,
            wallet_to=RECIP_KNOWN,
            amount="0.5",
            operator_id="mesa_01",
            as_of="2019-01-01T00:00:00Z",
        )
        state = analyze(op, repository=self.repo, policy=RiskPolicy(), use_llm=False)
        self.assertIn("audit_record", state)
        audit_rec = state["audit_record"]
        self.assertEqual(len(audit_rec["evidence_sha256"]), 64)
        self.assertEqual(audit_rec["operator_id"], "mesa_01")
        self.assertGreater(audit_rec["accountability_completeness"]["score"], 0.7)

        # Verify deterministic SHA-256 hash on identical state
        rec2 = build_audit_record(state)
        self.assertEqual(audit_rec["evidence_sha256"], rec2["evidence_sha256"])

        log_file = self.root / "audit.jsonl"
        append_audit_log(audit_rec, log_file)
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["evidence_sha256"], audit_rec["evidence_sha256"])

    def test_batch_analyze_and_dashboard_plot(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ops = [
            ProposedOperation.from_values(SENDER, RECIP_KNOWN, "0.5", operator_id="mesa_01"),
            ProposedOperation.from_values(SENDER, RECIP_UNKNOWN, "12.0", operator_id="mesa_01"),
        ]
        df_batch = batch_analyze(ops, repository=self.repo, policy=RiskPolicy(max_amount_eth=Decimal("10.0")), use_llm=False)
        self.assertEqual(len(df_batch), 2)
        self.assertIn("evidence_sha256", df_batch.columns)
        self.assertEqual(df_batch.iloc[1]["decision"], "BLOCK")

        state = analyze(ops[1], repository=self.repo, policy=RiskPolicy(max_amount_eth=Decimal("10.0")), use_llm=False)
        fig = plot_operator_dashboard(state)
        self.assertEqual(len(fig.axes), 4)
        plt.close(fig)

        fig2 = plot_assessment(state)
        self.assertEqual(len(fig2.axes), 4)
        plt.close(fig2)


if __name__ == "__main__":
    unittest.main()
