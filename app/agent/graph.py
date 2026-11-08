"""Entry point for the read-only on-chain operator agent (OONCA)."""

from __future__ import annotations

from collections.abc import Sequence
import pandas as pd

from app.ingestion.repository import WalletRepository
from app.ingestion.schema import ProposedOperation
from app.models.risk import RiskPolicy
from app.nodes.steps import AgentState, make_nodes


class _SequentialFallbackAgent:
    """Lightweight sequential runner used when `langgraph` is not installed in the active Python environment."""

    def __init__(self, steps):
        self._steps = steps

    def invoke(self, initial_state: AgentState) -> AgentState:
        state: dict = dict(initial_state)
        for step in self._steps:
            update = step(state)
            if update:
                state.update(update)
        return state  # type: ignore[return-value]


def build_agent(repository: WalletRepository | None = None, policy: RiskPolicy | None = None,
                use_llm: bool = True):
    repository = repository or WalletRepository()
    policy = policy or RiskPolicy()
    collect, score, explain, audit = make_nodes(repository, policy, use_llm)
    try:
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("collect_evidence", collect)
        graph.add_node("assess_risk", score)
        graph.add_node("explain", explain)
        graph.add_node("record_audit", audit)
        graph.add_edge(START, "collect_evidence")
        graph.add_edge("collect_evidence", "assess_risk")
        graph.add_edge("assess_risk", "explain")
        graph.add_edge("explain", "record_audit")
        graph.add_edge("record_audit", END)
        return graph.compile()
    except ImportError:
        return _SequentialFallbackAgent((collect, score, explain, audit))


def analyze(operation: ProposedOperation, *, repository: WalletRepository | None = None,
            policy: RiskPolicy | None = None, use_llm: bool = True) -> AgentState:
    return build_agent(repository, policy, use_llm).invoke({"operation": operation.as_state()})


def batch_analyze(
    operations: Sequence[ProposedOperation],
    *,
    repository: WalletRepository | None = None,
    policy: RiskPolicy | None = None,
    use_llm: bool = False,
) -> pd.DataFrame:
    """Evaluate a batch of hypothetical operations and return a comparative DataFrame."""
    repository = repository or WalletRepository()
    policy = policy or RiskPolicy()
    agent = build_agent(repository, policy, use_llm)
    rows: list[dict] = []
    for op in operations:
        state = agent.invoke({"operation": op.as_state()})
        op_dict = state["operation"]
        prof = state["profile"]
        assess_dict = state["assessment"]
        audit_rec = state.get("audit_record", {})
        auto_proxy = prof.get("automation_proxy", {}) or {}
        rows.append({
            "wallet_from": op_dict["wallet_from"],
            "wallet_to": op_dict["wallet_to"],
            "amount": float(op_dict["amount"]),
            "asset": op_dict["asset"],
            "operation": op_dict["operation"],
            "decision": assess_dict["decision"],
            "risk_score": assess_dict["risk_score"],
            "n_rows": prof.get("n_rows", 0),
            "n_unique_tx_hashes": prof.get("n_unique_tx_hashes", 0),
            "historical_error_rate": prof.get("historical_error_rate", 0.0),
            "recipient_seen": prof.get("recipient_seen", False),
            "automation_flagged": bool(auto_proxy.get("flagged", False)),
            "human_review_required": audit_rec.get("human_review_required", True),
            "accountability_score": audit_rec.get("accountability_completeness", {}).get("score", 0.0),
            "evidence_sha256": audit_rec.get("evidence_sha256", ""),
            "reasons": "; ".join(assess_dict.get("reasons", [])),
        })
    return pd.DataFrame(rows)
