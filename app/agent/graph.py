"""Entry point for the first read-only on-chain operator agent."""

from langgraph.graph import END, START, StateGraph

from app.ingestion.repository import WalletRepository
from app.ingestion.schema import ProposedOperation
from app.models.risk import RiskPolicy
from app.nodes.steps import AgentState, make_nodes


def build_agent(repository: WalletRepository | None = None, policy: RiskPolicy | None = None,
                use_llm: bool = True):
    repository = repository or WalletRepository()
    policy = policy or RiskPolicy()
    collect, score, explain = make_nodes(repository, policy, use_llm)
    graph = StateGraph(AgentState)
    graph.add_node("collect_evidence", collect)
    graph.add_node("assess_risk", score)
    graph.add_node("explain", explain)
    graph.add_edge(START, "collect_evidence")
    graph.add_edge("collect_evidence", "assess_risk")
    graph.add_edge("assess_risk", "explain")
    graph.add_edge("explain", END)
    return graph.compile()


def analyze(operation: ProposedOperation, *, repository: WalletRepository | None = None,
            policy: RiskPolicy | None = None, use_llm: bool = True) -> AgentState:
    return build_agent(repository, policy, use_llm).invoke({"operation": operation.as_state()})
