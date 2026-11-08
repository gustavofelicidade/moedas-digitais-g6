"""Explicit demo policy; scores are heuristic, not fraud probabilities."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskPolicy:
    max_amount_eth: Decimal | None = None
    review_threshold: int = 30
    policy_id: str = "default_triage_v2"
    min_error_observations: int = 20
    flag_automation_proxies: bool = True


def assess(operation: dict, profile: dict, policy: RiskPolicy) -> dict:
    reasons: list[str] = []
    rule_breakdown: list[dict] = []
    missing_data_flags: list[str] = [
        "token_contract_unobserved",
        "usd_price_unobserved",
    ]
    counterfactuals: list[str] = []
    score = 0

    def _record_rule(rule_id: str, category: str, points: int, triggered: bool, reason: str) -> None:
        nonlocal score
        if triggered:
            score += points
            reasons.append(reason)
        rule_breakdown.append({
            "rule_id": rule_id,
            "category": category,
            "points": points if triggered else 0,
            "max_points": points,
            "triggered": triggered,
            "reason": reason if triggered else None,
        })

    # Rule 1: Asset / operation coverage
    unsupported_op = operation["asset"] != "ETH" or operation["operation"] != "transfer"
    _record_rule(
        "asset_operation_coverage",
        "coverage",
        40,
        unsupported_op,
        "Tipo de operação ou ativo sem cobertura no dataset atual",
    )
    if unsupported_op:
        counterfactuals.append(
            "Fornecer dataset de eventos ERC-20/contratos decodificados para cobrir o ativo/operação propostos"
        )

    # Rule 2: Sender history presence
    no_history = profile["n_rows"] == 0
    _record_rule(
        "sender_history_presence",
        "history",
        35,
        no_history,
        "Carteira de origem sem histórico nesta amostra",
    )
    if no_history:
        counterfactuals.append(
            "Validar histórico da carteira de origem em fonte indexada contemporânea antes de aprovar"
        )

    # Rule 3: Unseen destination for this sender
    unseen_recipient = not profile["recipient_seen"]
    _record_rule(
        "recipient_novelty",
        "counterparty",
        15,
        unseen_recipient,
        "Destino não observado anteriormente para esta carteira",
    )
    if unseen_recipient:
        counterfactuals.append(
            "Confirmar endereço de destino na whitelist operacional ou verificar histórico prévio com o destinatário"
        )

    # Rule 4: Historical error / revert rate
    min_obs = policy.min_error_observations
    err_rate = profile.get("historical_error_rate")
    valid_obs = profile.get("valid_error_observations", profile["n_rows"])
    if valid_obs >= min_obs and err_rate is not None:
        if err_rate >= 0.5:
            _record_rule(
                "historical_error_rate",
                "operational_reliability",
                30,
                True,
                f"Alta proporção histórica de erros ({err_rate:.1%})",
            )
            counterfactuals.append(
                f"Inspecionar causa das reversões históricas ({err_rate:.1%} em {valid_obs} txs) e simular chamada via eth_call"
            )
        elif err_rate >= 0.2:
            _record_rule(
                "historical_error_rate",
                "operational_reliability",
                20,
                True,
                f"Proporção histórica de erros elevada ({err_rate:.1%})",
            )
            counterfactuals.append(
                f"Simular execução prévia da transação devido à taxa histórica de falhas ({err_rate:.1%})"
            )
        else:
            _record_rule("historical_error_rate", "operational_reliability", 30, False, "")
    else:
        _record_rule("historical_error_rate", "operational_reliability", 30, False, "")

    # Rule 5: Proposed value vs. 2x historical p95
    amount = Decimal(str(operation["amount"]))
    p95 = profile.get("p95_amount")
    exceeds_2x_p95 = bool(
        operation["asset"] == "ETH"
        and operation["operation"] == "transfer"
        and p95 is not None
        and p95 > 0
        and amount > Decimal(str(p95)) * 2
    )
    _record_rule(
        "amount_exceeds_2x_p95",
        "value_anomaly",
        20,
        exceeds_2x_p95,
        "Valor acima do dobro do percentil 95 histórico da carteira",
    )
    if exceeds_2x_p95 and p95 is not None:
        threshold_2x = Decimal(str(p95)) * 2
        counterfactuals.append(
            f"Reduzir o valor da operação para <= {threshold_2x:.4f} ETH (2x o p95 histórico da carteira) ou exigir revisão humana"
        )

    # Rule 6: Sender metadata coverage
    sender_meta_missing = profile.get("wallet_metadata") is None
    _record_rule(
        "sender_metadata_coverage",
        "metadata",
        10,
        sender_meta_missing,
        "Tipo da carteira não coberto pelo arquivo de metadados",
    )
    if sender_meta_missing:
        missing_data_flags.append("sender_metadata_missing")
        counterfactuals.append(
            "Executar enriquecimento ENS/RPC (py_files/ens_support.py) para a carteira de origem"
        )

    # Rule 7: Behavioral automation proxy (high-frequency / 24h cadence)
    auto_proxy = profile.get("automation_proxy") or {}
    auto_flagged = bool(policy.flag_automation_proxies and auto_proxy.get("flagged"))
    auto_signals = auto_proxy.get("signals") or []
    auto_reason = (
        "Padrão temporal compatível com automação/alta frequência (proxy comportamental): "
        + ", ".join(auto_signals)
        if auto_signals
        else "Padrão temporal compatível com automação/alta frequência (proxy comportamental)"
    )
    _record_rule(
        "behavioral_automation_proxy",
        "automation_proxy",
        15,
        auto_flagged,
        auto_reason,
    )
    if auto_flagged:
        counterfactuals.append(
            "Vincular operator_id e policy_id ao agente/automação para auditoria de operação automatizada"
        )

    # Rule 8: Recipient metadata & contract interaction check
    recipient_meta = profile.get("recipient_metadata")
    if recipient_meta is None:
        missing_data_flags.append("recipient_metadata_missing")
    elif recipient_meta.get("wallet_type") == "contract" and operation["operation"] == "transfer":
        _record_rule(
            "recipient_is_contract",
            "counterparty",
            10,
            True,
            "Destinatário identificado como contrato inteligente em operação de transferência simples",
        )
        counterfactuals.append(
            "Verificar se o contrato destinatário aceita transferências nativas (payable fallback/receive)"
        )

    if not operation.get("operator_id"):
        missing_data_flags.append("operator_id_unobserved")

    # Rule 9: Explicit policy hard limit block
    exceeds_max_eth = bool(
        policy.max_amount_eth is not None
        and operation["asset"] == "ETH"
        and operation["operation"] == "transfer"
        and amount > policy.max_amount_eth
    )
    _record_rule(
        "policy_max_amount_eth",
        "policy_limit",
        100,
        exceeds_max_eth,
        "Valor supera o limite configurado para ETH",
    )
    if exceeds_max_eth:
        decision = "BLOCK"
        score = 100
        counterfactuals.insert(
            0,
            f"Reduzir o valor proposto ({amount} ETH) para <= {policy.max_amount_eth} ETH (limite máximo da política '{policy.policy_id}')",
        )
    else:
        decision = "REVIEW" if score >= policy.review_threshold else "APPROVE"

    if decision == "APPROVE":
        counterfactuals = ["Nenhuma ação corretiva exigida pelas regras atuais deste protótipo"]

    return {
        "risk_score": min(score, 100),
        "decision": decision,
        "reasons": reasons or ["Nenhum sinal de revisão nas regras configuradas"],
        "rule_breakdown": rule_breakdown,
        "missing_data_flags": missing_data_flags,
        "counterfactuals": counterfactuals,
        "score_kind": "heuristic_not_probability",
        "policy": {
            "policy_id": policy.policy_id,
            "review_threshold": policy.review_threshold,
            "max_amount_eth": str(policy.max_amount_eth) if policy.max_amount_eth is not None else None,
            "min_error_observations": policy.min_error_observations,
            "flag_automation_proxies": policy.flag_automation_proxies,
        },
    }
