"""Explicit demo policy; scores are heuristic, not fraud probabilities."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskPolicy:
    max_amount_eth: Decimal | None = None
    review_threshold: int = 30


def assess(operation: dict, profile: dict, policy: RiskPolicy) -> dict:
    reasons = []
    score = 0
    if operation["asset"] != "ETH" or operation["operation"] != "transfer":
        reasons.append("Tipo de operação ou ativo sem cobertura no dataset atual")
        score += 40
    if profile["n_rows"] == 0:
        reasons.append("Carteira de origem sem histórico nesta amostra")
        score += 35
    if not profile["recipient_seen"]:
        reasons.append("Destino não observado anteriormente para esta carteira")
        score += 15
    if profile["n_rows"] >= 20 and profile["historical_error_rate"] is not None:
        rate = profile["historical_error_rate"]
        if rate >= .5:
            reasons.append(f"Alta proporção histórica de erros ({rate:.1%})")
            score += 30
        elif rate >= .2:
            reasons.append(f"Proporção histórica de erros elevada ({rate:.1%})")
            score += 20
    amount = Decimal(operation["amount"])
    p95 = profile["p95_amount"]
    if (operation["asset"] == "ETH" and operation["operation"] == "transfer"
            and p95 is not None and p95 > 0 and amount > Decimal(str(p95)) * 2):
        reasons.append("Valor acima do dobro do percentil 95 histórico da carteira")
        score += 20
    if profile["wallet_metadata"] is None:
        reasons.append("Tipo da carteira não coberto pelo arquivo de metadados")
        score += 10
    if (policy.max_amount_eth is not None and operation["asset"] == "ETH"
            and operation["operation"] == "transfer" and amount > policy.max_amount_eth):
        reasons.append("Valor supera o limite configurado para ETH")
        decision = "BLOCK"
        score = 100
    else:
        decision = "REVIEW" if score >= policy.review_threshold else "APPROVE"
    return {"risk_score": min(score, 100), "decision": decision,
            "reasons": reasons or ["Nenhum sinal de revisão nas regras configuradas"],
            "score_kind": "heuristic_not_probability",
            "policy": {"review_threshold": policy.review_threshold,
                       "max_amount_eth": str(policy.max_amount_eth) if policy.max_amount_eth is not None else None}}
